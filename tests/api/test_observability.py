"""Tests for structured logging, request IDs and the metrics endpoint."""

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.observability import (
    JsonLogFormatter,
    RequestObservabilityMiddleware,
    metrics_router,
    request_id_var,
    setup_logging,
)


def _make_client() -> TestClient:
    """A minimal app with the real middleware + metrics router mounted."""
    app = FastAPI()
    app.add_middleware(RequestObservabilityMiddleware)
    app.include_router(metrics_router, prefix="/api")

    @app.get("/api/ping")
    async def ping():
        return {"ok": True}

    return TestClient(app)


def test_response_carries_generated_request_id():
    client = _make_client()
    response = client.get("/api/ping")
    assert response.status_code == 200
    request_id = response.headers.get("x-request-id")
    assert request_id and len(request_id) >= 16


def test_incoming_request_id_is_propagated():
    client = _make_client()
    response = client.get("/api/ping", headers={"X-Request-ID": "trace-me-123"})
    assert response.headers.get("x-request-id") == "trace-me-123"


def test_metrics_endpoint_exposes_prometheus_format():
    client = _make_client()
    client.get("/api/ping")  # ensure at least one observation exists
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    # labels use the route template, not raw request paths
    assert 'path="/api/ping"' in body


def test_metrics_can_be_disabled(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENABLE_METRICS", False)
    client = _make_client()
    response = client.get("/api/metrics")
    assert response.status_code == 404


def test_json_formatter_emits_parseable_json_with_request_id():
    formatter = JsonLogFormatter()
    token = request_id_var.set("req-abc")
    try:
        record = logging.LogRecord(
            name="bloom.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        payload = json.loads(formatter.format(record))
    finally:
        request_id_var.reset(token)

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "bloom.test"
    assert payload["request_id"] == "req-abc"


def test_setup_logging_is_idempotent():
    setup_logging(level="INFO", json_logs=True)
    setup_logging(level="INFO", json_logs=True)
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonLogFormatter)
    # restore text logging so other tests' output stays readable
    setup_logging(level="INFO", json_logs=False)
