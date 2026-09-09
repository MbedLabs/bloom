"""One-time tokens must never appear in application/access logs."""

import logging

from fastapi.testclient import TestClient


def test_one_time_tokens_never_reach_access_logs(api_client: TestClient, caplog):
    secret = "SUPERSECRET-DO-NOT-LOG-0123456789abcdef"

    with caplog.at_level(logging.INFO):
        # Token in the POST body (the new invite-info contract) ...
        api_client.post("/api/auth/invite-info", json={"token": secret})
        # ... and, defensively, a legacy token in the query string.
        api_client.post(f"/api/auth/invite-info?token={secret}", json={"token": secret})

    # Inspect only the application's own log records (the httpx test client logs
    # its outbound URL, which is a test-harness artifact, not production logging).
    app_logs = "\n".join(
        r.getMessage() for r in caplog.records if r.name.startswith(("bloom", "app"))
    )
    assert "/api/auth/invite-info" in app_logs
    assert secret not in app_logs
