"""Operational instrumentation: structured logging, request IDs, Prometheus metrics and the
request's audit event."""

from __future__ import annotations

import ipaddress
import json
import logging
import sys
import time
import uuid
import zlib
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)
user_agent_var: ContextVar[str | None] = ContextVar("user_agent", default=None)

access_logger = logging.getLogger("bloom.access")
logger = logging.getLogger(__name__)

CREATED_BODY_LIMIT = 1024 * 1024


@dataclass
class RequestAudit:
    """What handling one request learned for its audit event: the actor, the client kind of a
    user token, the service credential and whether a 404 hid something the actor may not see."""

    actor_type: Optional[str] = None
    actor_user_id: Optional[int] = None
    client: Optional[str] = None
    service_credential_id: Optional[int] = None
    refused: bool = False


request_audit_var: ContextVar[Optional[RequestAudit]] = ContextVar("request_audit", default=None)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP requests processed, by method, route template and status code.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency, by method and route template.",
    ["method", "path"],
)


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line; safe for log shippers."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "http", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestIdTextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_var.get()
        return super().format(record)


def setup_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configure root logging exactly once (idempotent on repeat calls)."""
    handler = logging.StreamHandler(sys.stdout)
    if json_logs:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            RequestIdTextFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s"
            )
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


class CreatedBody:
    """The JSON body of a 201 answer, kept up to CREATED_BODY_LIMIT bytes, gzip or plain."""

    def __init__(self, gzipped: bool):
        self.gzipped = gzipped
        self.chunks: list[bytes] = []
        self.size = 0
        self.overflow = False

    def feed(self, chunk: bytes) -> None:
        """Keep the chunk while the body stays within the limit."""
        if self.overflow or not chunk:
            return
        self.size += len(chunk)
        if self.size > CREATED_BODY_LIMIT:
            self.overflow = True
            self.chunks = []
            return
        self.chunks.append(chunk)

    def parsed(self) -> Any:
        """The decoded JSON value, or None when the body is too large or not JSON."""
        if self.overflow or not self.chunks:
            return None
        raw = b"".join(self.chunks)
        try:
            if self.gzipped:
                inflater = zlib.decompressobj(zlib.MAX_WBITS | 16)
                raw = inflater.decompress(raw, CREATED_BODY_LIMIT + 1)
                if len(raw) > CREATED_BODY_LIMIT:
                    return None
            return json.loads(raw)
        except (zlib.error, ValueError):
            return None


def _created_body(message: dict) -> Optional[CreatedBody]:
    """A collector for a 201 JSON answer in plain or gzip encoding, else None."""
    if message["status"] != 201:
        return None
    headers = {k.lower(): v for k, v in message.get("headers", [])}
    content_type = headers.get(b"content-type", b"").split(b";")[0].strip()
    if content_type != b"application/json":
        return None
    encoding = headers.get(b"content-encoding", b"").strip().lower()
    if encoding not in (b"", b"identity", b"gzip"):
        return None
    return CreatedBody(gzipped=encoding == b"gzip")


IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@lru_cache(maxsize=8)
def _networks(entries: tuple[str, ...]) -> tuple[IPNetwork, ...]:
    """The trusted proxy networks named by the setting's entries."""
    return tuple(ipaddress.ip_network(entry.strip(), strict=False) for entry in entries)


def _address(value: str) -> Optional[IPAddress]:
    """The IP address of a peer or X-Forwarded-For entry, without a port; an IPv4-mapped
    IPv6 address as IPv4; None when the value is not an address."""
    value = value.strip()
    if value.startswith("["):
        value = value[1 : value.find("]")] if "]" in value else ""
    elif value.count(":") == 1:
        value = value.split(":", 1)[0]
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


def _trusted(address: Optional[IPAddress], networks: tuple[IPNetwork, ...]) -> bool:
    """Whether the address lies in one of the trusted proxy networks."""
    return address is not None and any(address in network for network in networks)


def client_address(scope) -> Optional[str]:
    """The client address of a request: the direct peer, or, when the peer is in
    TRUSTED_PROXY_NETWORKS, the right-most X-Forwarded-For entry outside those networks.
    An entry that is not an address ends the walk at the last trusted hop."""
    from app.core.config import settings

    client = scope.get("client")
    peer = client[0] if client else None
    networks = _networks(tuple(settings.TRUSTED_PROXY_NETWORKS))
    if peer is None or not networks or not _trusted(_address(peer), networks):
        return peer
    forwarded = ",".join(
        value.decode("latin-1")
        for name, value in scope.get("headers", [])
        if name.lower() == b"x-forwarded-for"
    )
    resolved = peer
    for entry in reversed(forwarded.split(",") if forwarded else []):
        address = _address(entry)
        if address is None:
            break
        resolved = str(address)
        if not _trusted(address, networks):
            break
    return resolved


class RequestObservabilityMiddleware:
    """Pure ASGI middleware: request id, access log, metrics and one audit event per request,
    written when the response is finished."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v for k, v in scope.get("headers", [])}
        incoming = headers.get("x-request-id", b"").decode("latin-1").strip()
        request_id = incoming[:64] if incoming else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        ip_token = client_ip_var.set(client_address(scope))
        agent = headers.get("user-agent", b"").decode("latin-1")
        agent_token = user_agent_var.set(agent or None)
        audit_token = request_audit_var.set(RequestAudit())

        status_code = 500
        created: Optional[CreatedBody] = None
        start = time.perf_counter()

        async def send_wrapper(message):
            nonlocal status_code, created
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", [])
                message["headers"] = [
                    (k, v) for k, v in message["headers"] if k.lower() != b"x-request-id"
                ] + [(b"x-request-id", request_id.encode("latin-1"))]
                created = _created_body(message)
            elif message["type"] == "http.response.body" and created is not None:
                created.feed(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            route = scope.get("route")
            path_template = getattr(route, "path", None) or "unmatched"
            method = scope.get("method", "-")
            HTTP_REQUESTS_TOTAL.labels(method, path_template, str(status_code)).inc()
            HTTP_REQUEST_DURATION.labels(method, path_template).observe(duration)
            access_logger.info(
                "%s %s %s %.1fms",
                method,
                scope.get("path", "-"),
                status_code,
                duration * 1000,
                extra={
                    "http": {
                        "method": method,
                        "path": scope.get("path", "-"),
                        "route": path_template,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 1),
                    }
                },
            )
            try:
                await _record_request(
                    scope,
                    headers,
                    status_code,
                    round(duration * 1000, 1),
                    created.parsed() if created is not None else None,
                )
            finally:
                request_id_var.reset(token)
                client_ip_var.reset(ip_token)
                user_agent_var.reset(agent_token)
                request_audit_var.reset(audit_token)


async def _record_request(
    scope, headers: dict, status_code: int, duration_ms: float, created_body: Any
) -> None:
    """Write the request's audit event; a failure is logged and leaves the response as sent."""
    from app.services.audit import record_request_event

    try:
        await record_request_event(
            scope,
            authorization=headers.get("authorization", b"").decode("latin-1"),
            status_code=status_code,
            duration_ms=duration_ms,
            created_body=created_body,
        )
    except Exception:
        logger.exception("Audit event api.request could not be recorded")


metrics_router = APIRouter()


@metrics_router.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    from app.core.config import settings

    if not settings.ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Not Found")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
