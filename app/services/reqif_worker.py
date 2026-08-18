"""Killable child-process boundary for CPU-bound ReqIF parsing."""

from __future__ import annotations

import asyncio
import multiprocessing
from multiprocessing.connection import Connection

from app.core.config import settings
from app.core.reqif import ReqIFBundle, ReqIFParseError, parse_reqif


class ReqIFProcessingTimeout(TimeoutError):
    """Raised after terminating a parser process that exceeded its deadline."""


def _worker_entry(data: bytes, sender: Connection) -> None:
    try:
        sender.send(("ok", parse_reqif(data)))
    except ReqIFParseError as exc:
        sender.send(("invalid", str(exc)))
    except BaseException:
        sender.send(("error", "ReqIF parser worker failed."))
    finally:
        sender.close()


def _parse_in_process(data: bytes, timeout_seconds: float) -> ReqIFBundle:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_worker_entry, args=(data, sender), daemon=True)
    process.start()
    sender.close()
    try:
        if not receiver.poll(timeout_seconds):
            process.terminate()
            process.join(timeout=5)
            raise ReqIFProcessingTimeout("ReqIF processing exceeded the 60-second timeout.")
        kind, payload = receiver.recv()
        process.join(timeout=5)
        if kind == "ok":
            return payload
        if kind == "invalid":
            raise ReqIFParseError(payload)
        raise ReqIFParseError("ReqIF parser worker failed.")
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)


async def parse_reqif_in_worker(
    data: bytes, *, timeout_seconds: float | None = None
) -> ReqIFBundle:
    timeout = (
        settings.REQIF_PROCESSING_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    )
    return await asyncio.to_thread(_parse_in_process, data, timeout)
