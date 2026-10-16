"""Killable child-process boundary for CPU-bound import parsing (ReqIF, TestRail)."""

from __future__ import annotations

import asyncio
import multiprocessing
from multiprocessing.connection import Connection
from typing import Any, Callable

from app.core.config import settings
from app.core.reqif import ReqIFBundle, ReqIFParseError, parse_reqif


class ReqIFProcessingTimeout(TimeoutError):
    """Raised after terminating a parser process that exceeded its deadline."""


def _worker_entry(
    parser: Callable[[bytes], Any], expected: type, data: bytes, sender: Connection
) -> None:
    try:
        sender.send(("ok", parser(data)))
    except expected as exc:
        sender.send(("invalid", str(exc)))
    except BaseException:
        sender.send(("error", ""))
    finally:
        sender.close()


def _run_in_process(
    parser: Callable[[bytes], Any],
    data: bytes,
    timeout_seconds: float,
    error_cls: type,
    label: str,
) -> Any:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker_entry, args=(parser, error_cls, data, sender), daemon=True
    )
    process.start()
    sender.close()
    try:
        if not receiver.poll(timeout_seconds):
            process.terminate()
            process.join(timeout=5)
            raise ReqIFProcessingTimeout(f"{label} processing exceeded the 60-second timeout.")
        kind, payload = receiver.recv()
        process.join(timeout=5)
        if kind == "ok":
            return payload
        if kind == "invalid":
            raise error_cls(payload)
        raise error_cls(f"{label} parser worker failed.")
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)


def _parse_in_process(data: bytes, timeout_seconds: float) -> ReqIFBundle:
    return _run_in_process(parse_reqif, data, timeout_seconds, ReqIFParseError, "ReqIF")


async def parse_reqif_in_worker(
    data: bytes, *, timeout_seconds: float | None = None
) -> ReqIFBundle:
    timeout = (
        settings.REQIF_PROCESSING_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    )
    return await asyncio.to_thread(_parse_in_process, data, timeout)


async def parse_in_worker(
    parser: Callable[[bytes], Any],
    data: bytes,
    *,
    error_cls: type,
    label: str,
    timeout_seconds: float | None = None,
) -> Any:
    """Run a module-level parser in a killable child process with the import timeout."""
    timeout = (
        settings.REQIF_PROCESSING_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    )
    return await asyncio.to_thread(_run_in_process, parser, data, timeout, error_cls, label)
