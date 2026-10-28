"""The client address of audit events behind a reverse proxy: X-Forwarded-For is read only
when the request comes from a network in TRUSTED_PROXY_NETWORKS, through the image's chain of
an outer proxy, the image's nginx and uvicorn."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import Settings, settings
from app.core.observability import client_address
from app.main import app
from tests.sec.test_audit_log_http import _events, harness  # noqa: F401
from tests.sec.test_request_audit_http import _one

PROXY = "10.0.0.2"
PROXY_NETWORK = "10.0.0.0/8"
CALLER = "203.0.113.7"
OTHER_CALLER = "203.0.113.8"
FORGED = "198.51.100.9"
OUTSIDER = "192.0.2.50"
FORGED_TOKEN = {"Authorization": "Bearer forged"}
SECRET = "test-secret-key-for-trusted-proxy-settings-1234567890"


def _image_client():
    """A client that reaches the app as the image's nginx does: from 127.0.0.1, through
    uvicorn's proxy header handling with its default trusted addresses."""
    return TestClient(
        ProxyHeadersMiddleware(app, trusted_hosts="127.0.0.1,::1"),
        base_url="http://test",
        client=("127.0.0.1", 50000),
    )


def _via_nginx(received_from, forwarded=None):
    """The headers the image's nginx sends: the X-Forwarded-For it received with the address
    it received the request from appended."""
    chain = f"{forwarded}, {received_from}" if forwarded else received_from
    return {**FORGED_TOKEN, "X-Forwarded-For": chain}


@pytest.fixture
def trusted_proxy(monkeypatch):
    """TRUSTED_PROXY_NETWORKS names the outer proxy's network."""
    monkeypatch.setattr(settings, "TRUSTED_PROXY_NETWORKS", [PROXY_NETWORK])


def test_a_trusted_proxy_forwards_the_callers_address(harness, trusted_proxy):
    _, session_maker = harness
    client = _image_client()

    plain = client.get("/api/projects", headers=_via_nginx(PROXY, CALLER))
    forged = client.get("/api/projects", headers=_via_nginx(PROXY, f"{FORGED}, {CALLER}"))

    assert (plain.status_code, forged.status_code) == (401, 401)
    assert _one(session_maker, plain).ip == CALLER
    assert _one(session_maker, forged).ip == CALLER


def test_a_forged_header_from_an_untrusted_sender_is_ignored(harness, trusted_proxy):
    _, session_maker = harness
    client = _image_client()

    forged = client.get("/api/projects", headers=_via_nginx(OUTSIDER, FORGED))
    posing = client.get("/api/projects", headers=_via_nginx(OUTSIDER, f"{FORGED}, 10.0.0.3"))
    direct = TestClient(app, base_url="http://test", client=(OUTSIDER, 50000)).get(
        "/api/projects", headers={**FORGED_TOKEN, "X-Forwarded-For": FORGED}
    )

    assert _one(session_maker, forged).ip == OUTSIDER
    assert _one(session_maker, posing).ip == OUTSIDER
    assert _one(session_maker, direct).ip == OUTSIDER


def test_the_empty_default_records_the_direct_peer(harness):
    _, session_maker = harness
    assert Settings(SECRET_KEY=SECRET, _env_file=None).TRUSTED_PROXY_NETWORKS == []
    assert settings.TRUSTED_PROXY_NETWORKS == []

    proxied = _image_client().get("/api/projects", headers=_via_nginx(PROXY, CALLER))
    direct = TestClient(app, base_url="http://test", client=(OUTSIDER, 50000)).get(
        "/api/projects", headers={**FORGED_TOKEN, "X-Forwarded-For": FORGED}
    )

    assert _one(session_maker, proxied).ip == PROXY
    assert _one(session_maker, direct).ip == OUTSIDER


def _refuse(client, callers):
    """One denied request through the outer proxy for each caller address, in order."""
    for caller in callers:
        assert client.get("/api/projects", headers=_via_nginx(PROXY, caller)).status_code == 401


def test_repeated_refusals_are_counted_by_the_forwarded_address(
    harness, trusted_proxy, monkeypatch
):
    _, session_maker = harness
    monkeypatch.setattr(settings, "AUDIT_REFUSAL_THRESHOLD", 3)

    _refuse(_image_client(), [CALLER, CALLER, OTHER_CALLER, OTHER_CALLER, CALLER])

    [detected] = _events(session_maker, "security.repeated_refusals")
    assert detected.ip == CALLER
    assert detected.details["address"] == CALLER
    assert detected.details["count"] == 3


def test_without_trusted_proxies_refusals_are_counted_by_the_proxy(harness, monkeypatch):
    _, session_maker = harness
    monkeypatch.setattr(settings, "AUDIT_REFUSAL_THRESHOLD", 3)

    _refuse(_image_client(), [CALLER, OTHER_CALLER, CALLER])

    [detected] = _events(session_maker, "security.repeated_refusals")
    assert detected.details["address"] == PROXY


def _scope(peer, *forwarded):
    """An HTTP scope from the peer with one X-Forwarded-For header per value."""
    return {
        "type": "http",
        "client": (peer, 50000) if peer else None,
        "headers": [(b"x-forwarded-for", value.encode("latin-1")) for value in forwarded],
    }


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        (_scope(PROXY), PROXY),
        (_scope(None, CALLER), None),
        (_scope(PROXY, f"{FORGED}, {CALLER}, 10.0.0.9"), CALLER),
        (_scope(PROXY, FORGED, CALLER), CALLER),
        (_scope(PROXY, f"{CALLER}:4711"), CALLER),
        (_scope(PROXY, "[2001:db8::7]:4711"), "2001:db8::7"),
        (_scope(f"::ffff:{PROXY}", CALLER), CALLER),
        (_scope(PROXY, f"{CALLER}, not-an-address, 10.0.0.9"), "10.0.0.9"),
        (_scope(PROXY, "10.0.0.8, 10.0.0.9"), "10.0.0.8"),
        (_scope(PROXY, ""), PROXY),
        (_scope(OUTSIDER, CALLER), OUTSIDER),
        (_scope("testclient", CALLER), "testclient"),
    ],
)
def test_the_client_address_is_the_right_most_untrusted_hop(monkeypatch, scope, expected):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_NETWORKS", [PROXY_NETWORK])

    assert client_address(scope) == expected


def test_the_setting_reads_a_json_array_of_networks(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_NETWORKS", '["10.1.2.3/8", " 2001:db8::/32 ", "192.0.2.1"]')

    loaded = Settings(SECRET_KEY=SECRET, _env_file=None)

    assert loaded.TRUSTED_PROXY_NETWORKS == ["10.0.0.0/8", "2001:db8::/32", "192.0.2.1/32"]


def test_the_setting_refuses_an_entry_that_is_not_a_network():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY=SECRET, _env_file=None, TRUSTED_PROXY_NETWORKS=["proxy.example"])
