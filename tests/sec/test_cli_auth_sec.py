"""CLI authorization rejects redirect abuse, replay and revoked identities."""

import asyncio
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, update

from app.core.security import create_access_token
from app.models import AuditEvent, User, UserToken, UserTokenPurpose
from app.models.cli_auth_session import CliAuthSession
from app.schemas.cli_auth import CliStartRequest
from app.services import cli_auth
from tests.api.test_cli_auth import (
    CHALLENGE,
    PREFIX,
    VERIFIER,
    approve,
    audit_rows,
    bearer,
    cli_client,
    exchange,
    run_db,
    signed_in,
    start,
)

__all__ = ["cli_client"]


@pytest.mark.parametrize(
    "uri",
    [
        "https://127.0.0.1:8123/callback",
        "http://example.com:8123/callback",
        "http://127.0.0.2:8123/callback",
        "http://localhost.evil.test:8123/callback",
        "http://localhost/callback",
        "http://localhost:0/callback",
        "http://localhost:65536/callback",
        "http://localhost:port/callback",
        "http://user:password@localhost:8123/callback",
        "http://127.0.0.1:80@evil.test/callback",
        "http://localhost:8123/callback#fragment",
        "http://localhost:8123/callback?code=existing",
        "http://localhost:8123/callback?state=existing",
        "http://localhost:8123/callback?%63ode=existing",
        "http://localhost:8123/callback?STATE=existing",
        "http://localhost:8123/callback?code",
        "http://localhost:8123/callback?x=a&state=b",
        "http://127.1:8123/callback",
        "http://2130706433:8123/callback",
        "//localhost:8123/callback",
        "http://localhost:8123/call\\back",
        "http://local\nhost:8123/callback",
        "http://localhost:8123/call back",
    ],
)
def test_callback_redirect_abuse_is_rejected(cli_client, uri):
    client, *_ = cli_client
    response = client.post(
        PREFIX + "/start",
        json={
            "client_name": "Client",
            "mode": "callback",
            "redirect_uri": uri,
            "code_challenge": CHALLENGE,
            "state": "state",
        },
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "change",
    [
        {"code_challenge": "short"},
        {"code_challenge": "a" * 42 + "="},
        {"code_challenge": "a" * 44},
        {"state": ""},
        {"state": "s" * 129},
        {"client_name": " "},
        {"client_name": "c" * 101},
        {"mode": "callback"},
        {"mode": "other"},
        {"mode": "code", "redirect_uri": "http://localhost:8123/callback"},
        {"extra": "field"},
    ],
)
def test_invalid_start_fields_are_rejected(cli_client, change):
    client, *_ = cli_client
    response = client.post(
        PREFIX + "/start",
        json={
            "client_name": "Client",
            "mode": "code",
            "code_challenge": CHALLENGE,
            "state": "state",
            **change,
        },
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("verifier", ["x" * 43, "short", "x" * 129, "+" * 43])
def test_invalid_pkce_does_not_consume_or_issue_tokens(cli_client, verifier):
    client, maker, headers, _, _ = cli_client
    session = start(client)
    code = approve(client, headers, session["session_id"])["exchange_code"]
    response = exchange(client, session["session_id"], code, verifier)
    assert response.status_code in (400, 422)
    assert not run_db(maker, lambda db: db.scalars(select(UserToken))).all()
    assert not [e for e in audit_rows(maker, "auth.cli_exchange") if e.outcome == "success"]
    assert exchange(client, session["session_id"], code).status_code == 200


def test_exchange_code_and_refresh_token_lengths_are_bounded(cli_client):
    client, _, headers, _, _ = cli_client
    session = start(client)
    approve(client, headers, session["session_id"])
    assert exchange(client, session["session_id"], "c" * 257).status_code == 422
    assert exchange(client, session["session_id"], "c" * 256).status_code == 400
    too_long = client.post(PREFIX + "/refresh", json={"refresh_token": "r" * 257})
    assert too_long.status_code == 422
    assert client.post(PREFIX + "/refresh", json={"refresh_token": "r" * 256}).status_code == 401


def test_wrong_code_and_unapproved_unknown_sessions_reject(cli_client):
    client, maker, headers, _, _ = cli_client
    session = start(client)
    assert exchange(client, session["session_id"], "unapproved").status_code == 400
    code = approve(client, headers, session["session_id"])["exchange_code"]
    assert exchange(client, session["session_id"], "wrong-code").status_code == 400
    unknown = str(uuid4())
    assert exchange(client, unknown, code).status_code == 400
    assert client.get(PREFIX + "/sessions/" + str(uuid4()), headers=headers).status_code == 400
    failures = audit_rows(maker, "auth.cli_exchange")
    assert [(e.outcome, e.target_id, e.details) for e in failures] == [
        ("failure", session["session_id"], {"reason": "unknown_or_unapproved_session"}),
        ("failure", session["session_id"], {"reason": "code_or_verifier_mismatch"}),
        ("failure", unknown, {"reason": "unknown_or_unapproved_session"}),
    ]
    assert all(e.actor_user_id is None for e in failures)
    assert all(code not in str(e.details) for e in failures)
    assert exchange(client, session["session_id"], code).status_code == 200


@pytest.mark.parametrize("approved", [False, True])
def test_expired_session_cannot_approve_or_exchange(cli_client, approved):
    client, maker, headers, _, _ = cli_client
    session = start(client)
    code = (
        approve(client, headers, session["session_id"])["exchange_code"] if approved else "unused"
    )
    run_db(
        maker,
        lambda db: db.execute(
            update(CliAuthSession)
            .where(CliAuthSession.id == UUID(session["session_id"]))
            .values(expires_at=datetime.utcnow() - timedelta(seconds=1))
        ),
    )
    assert (
        client.get(PREFIX + "/sessions/" + session["session_id"], headers=headers).status_code
        == 400
    )
    assert (
        client.post(
            PREFIX + "/approve", headers=headers, json={"session_id": session["session_id"]}
        ).status_code
        == 400
    )
    assert exchange(client, session["session_id"], code).status_code == 400


def test_disabled_account_rejects_approval_exchange_and_refresh(cli_client):
    client, maker, headers, user_id, _ = cli_client
    tokens = signed_in(client, start(client)["session_id"], headers)
    pending = start(client)
    waiting = start(client)
    approved_code = approve(client, headers, waiting["session_id"])["exchange_code"]
    run_db(
        maker, lambda db: db.execute(update(User).where(User.id == user_id).values(is_active=False))
    )
    assert (
        client.post(
            PREFIX + "/approve", headers=headers, json={"session_id": pending["session_id"]}
        ).status_code
        == 403
    )
    assert exchange(client, waiting["session_id"], approved_code).status_code == 400
    refresh = client.post(PREFIX + "/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401
    failure = audit_rows(maker, "auth.cli_refresh")[-1]
    assert (failure.outcome, failure.target_type, failure.target_id, failure.details) == (
        "failure",
        "user",
        str(user_id),
        {"reason": "inactive_or_missing_user"},
    )


def test_approval_rereads_and_rejects_a_changed_account(cli_client):
    _, maker, _, user_id, _ = cli_client
    session = run_db(
        maker,
        lambda db: cli_auth.start_session(
            db,
            CliStartRequest(
                client_name="Client", mode="code", code_challenge=CHALLENGE, state="state"
            ),
        ),
    )

    async def approve_with_stale_account():
        async with maker() as db:
            account = await db.get(User, user_id)
            async with maker() as other:
                await other.execute(
                    update(User).where(User.id == user_id).values(session_version=2)
                )
                await other.commit()
            with pytest.raises(cli_auth.CliAuthorizationError) as refused:
                await cli_auth.approve_session(db, session.id, account)
            return refused.value.reason

    assert asyncio.run(approve_with_stale_account()) == "inactive_or_changed_user"
    stored = run_db(maker, lambda db: db.get(CliAuthSession, session.id))
    assert stored.user_id is None and stored.exchange_code_hash is None


@pytest.mark.parametrize("binding", [None, True, "1", -1, 999999])
def test_cli_access_requires_valid_matching_refresh_binding(cli_client, binding):
    client, _, _, user_id, _ = cli_client
    token = create_access_token(
        {"sub": str(user_id), "type": "user", "ver": 1, "cli_refresh_id": binding}
    )
    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 401


@pytest.mark.parametrize("mutation", ["expired", "purpose", "user", "version"])
def test_cli_access_rejects_invalidated_binding(cli_client, mutation):
    client, maker, headers, user_id, other_id = cli_client
    tokens = signed_in(client, start(client)["session_id"], headers)
    if mutation == "version":
        run_db(
            maker,
            lambda db: db.execute(update(User).where(User.id == user_id).values(session_version=2)),
        )
    else:
        values = {
            "expired": {"expires_at": datetime.utcnow() - timedelta(seconds=1)},
            "purpose": {"purpose": UserTokenPurpose.password_reset},
            "user": {"user_id": other_id},
        }[mutation]
        run_db(maker, lambda db: db.execute(update(UserToken).values(**values)))
    assert client.get("/api/auth/me", headers=bearer(tokens["access_token"])).status_code == 401


def test_cli_refresh_missing_and_unknown_tokens_reject(cli_client):
    client, maker, *_ = cli_client
    assert client.post(PREFIX + "/refresh", json={"refresh_token": "unknown"}).status_code == 401
    assert client.post(PREFIX + "/refresh", json={}).status_code == 422
    failure = audit_rows(maker, "auth.cli_refresh")[-1]
    assert (failure.outcome, failure.target_type, failure.details) == (
        "failure",
        None,
        {"reason": "invalid_token"},
    )
    assert "unknown" not in str(failure.details)


def test_failure_audits_carry_no_secret(cli_client):
    client, maker, headers, _, _ = cli_client
    session = start(client)
    code = approve(client, headers, session["session_id"])["exchange_code"]
    exchange(client, session["session_id"], code, "w" * 43)
    tokens = signed_in(client, start(client)["session_id"], headers)
    client.post(PREFIX + "/refresh", json={"refresh_token": tokens["refresh_token"]})
    client.post(PREFIX + "/refresh", json={"refresh_token": tokens["refresh_token"]})

    async def every_event(db):
        return (await db.scalars(select(AuditEvent))).all()

    events = run_db(maker, every_event)
    assert {e.outcome for e in events} == {"success", "failure"}
    text = " ".join(f"{e.target_id} {e.details}" for e in events)
    for secret in (code, VERIFIER, "w" * 43, tokens["refresh_token"], tokens["access_token"]):
        assert secret not in text


@pytest.mark.parametrize(
    "path,body,limit",
    [
        (
            "start",
            {
                "client_name": "Rate test",
                "mode": "code",
                "code_challenge": CHALLENGE,
                "state": "rate-state",
            },
            10,
        ),
        (
            "exchange",
            {"session_id": str(uuid4()), "code": "unknown", "code_verifier": VERIFIER},
            30,
        ),
        ("refresh", {"refresh_token": "unknown"}, 30),
    ],
)
def test_public_cli_endpoints_enforce_their_rate_limit(cli_client, monkeypatch, path, body, limit):
    from app.core.deps import limiter

    client, *_ = cli_client
    limiter.reset()
    monkeypatch.setattr(limiter, "enabled", True)
    responses = [client.post(f"{PREFIX}/{path}", json=body) for _ in range(limit + 1)]
    assert all(response.status_code != 429 for response in responses[:-1])
    assert responses[-1].status_code == 429
