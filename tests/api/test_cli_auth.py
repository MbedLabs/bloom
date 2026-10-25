"""Browser-approved CLI sessions retain Bloom's existing account authority."""

import asyncio
import base64
import hashlib
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token, get_current_user
from app.main import app
from app.models import AuditEvent, Policy, Project, User, UserToken, UserTokenPurpose
from app.models.cli_auth_session import CliAuthSession
from app.models.groups import user_application_policies
from app.models.user import UserRole
from app.services import cli_auth
from app.services.token_service import create_user_token, invalidate_all_refresh_tokens
from tests.access_fixtures import project_access_fixture

VERIFIER = "v" * 43
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
)
RFC7636_VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
RFC7636_CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
RFC7636_REQUEST_CODE = "BUUZ-WHVV"
PREFIX = "/api/auth/cli"
REFRESH_COOKIE = "bloom_refresh_token"
SESSION_FIELDS = {
    "session_id",
    "client_name",
    "mode",
    "redirect_uri",
    "expires_at",
    "consumed",
    "created_at",
    "request_code",
}


@pytest.fixture
def cli_client(monkeypatch):
    """Use real JWT guards and permission resolution on an isolated database with code sign-in on."""
    monkeypatch.setattr(settings, "CLI_CODE_MODE_ENABLED", True)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def seed():
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            await conn.run_sync(Base.metadata.create_all)
        async with maker() as db:
            user = User(
                email="cli-reader@example.com",
                full_name="CLI Reader",
                hashed_password="unused",
                role=UserRole.maintainer,
                is_active=True,
            )
            other = User(
                email="other@example.com",
                full_name="Other",
                hashed_password="unused",
                role=UserRole.external,
                is_active=True,
            )
            project = Project(name="CLI Project", prefix="CLI")
            policy = Policy(name="App reader", scope="app", permissions={"application": ["view"]})
            db.add_all([user, other, project, policy])
            await db.flush()
            db.add(
                project_access_fixture(
                    user_id=user.id, project_id=project.id, permissions={"REQ": ["view"]}
                )
            )
            await db.execute(
                user_application_policies.insert().values(user_id=user.id, policy_id=policy.id)
            )
            await db.commit()
            return user.id, other.id

    async def database():
        async with maker() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    user_id, other_id = asyncio.run(seed())
    app.dependency_overrides[get_db] = database
    headers = {
        "Authorization": "Bearer "
        + create_access_token({"sub": str(user_id), "type": "user", "ver": 1})
    }
    client = TestClient(app, base_url="http://test")
    try:
        yield client, maker, headers, user_id, other_id
    finally:
        client.close()
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


def start(client, **overrides):
    """Request a valid manual-code session with independently calculated PKCE."""
    response = client.post(
        PREFIX + "/start",
        json={
            "client_name": "Example client",
            "mode": "code",
            "code_challenge": CHALLENGE,
            "state": "test-state",
            **overrides,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def approve(client, headers, session_id):
    """Approve a session as the signed-in user and return the approval body."""
    response = client.post(PREFIX + "/approve", headers=headers, json={"session_id": session_id})
    assert response.status_code == 200, response.text
    return response.json()


def exchange(client, session_id, code, verifier=VERIFIER):
    """Post one exchange request."""
    return client.post(
        PREFIX + "/exchange",
        json={"session_id": session_id, "code": code, "code_verifier": verifier},
    )


def deny(client, headers, session_id):
    """Post one deny request as the signed-in user."""
    return client.post(PREFIX + "/deny", headers=headers, json={"session_id": session_id})


def stored_ids(maker):
    """Return the ids of every stored authorization session."""

    async def ids(db):
        return {str(value) for value in (await db.scalars(select(CliAuthSession.id))).all()}

    return run_db(maker, ids)


def signed_in(client, session_id, headers):
    """Approve and exchange a manual-code session and return the issued credentials."""
    code = approve(client, headers, session_id)["exchange_code"]
    response = exchange(client, session_id, code)
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token):
    """Authorization header for an access token."""
    return {"Authorization": "Bearer " + token}


def run_db(maker, action):
    """Commit one isolated database operation and return its result."""

    async def run():
        async with maker() as db:
            result = await action(db)
            await db.commit()
            return result

    return asyncio.run(run())


def audit_rows(maker, action):
    """Return the audit rows recorded for one action, oldest first."""

    async def rows(db):
        return (
            await db.scalars(
                select(AuditEvent).where(AuditEvent.action == action).order_by(AuditEvent.id)
            )
        ).all()

    return run_db(maker, rows)


def test_manual_exchange_preserves_user_permissions_and_hashes_secrets(cli_client):
    client, maker, headers, user_id, _ = cli_client
    created = start(client)
    assert created["expires_at"].endswith("Z")
    assert urlsplit(created["authorize_url"]).path == "/auth/cli"
    assert parse_qs(urlsplit(created["authorize_url"]).query) == {
        "session_id": [created["session_id"]]
    }
    expiry = datetime.fromisoformat(created["expires_at"].replace("Z", "+00:00")).replace(
        tzinfo=None
    )
    assert timedelta(minutes=9) < expiry - datetime.utcnow() <= timedelta(minutes=10)
    metadata = client.get(PREFIX + "/sessions/" + created["session_id"], headers=headers)
    assert metadata.status_code == 200, metadata.text
    assert set(metadata.json()) == SESSION_FIELDS
    assert metadata.json()["client_name"] == "Example client"
    assert metadata.headers["cache-control"] == "no-store"
    assert (
        not {"code", "exchange_code_hash", "code_challenge", "state", "user_id"}
        & metadata.json().keys()
    )
    approval = approve(client, headers, created["session_id"])
    assert approval["expires_at"].endswith("Z")
    assert set(approval) == {"exchange_code", "expires_at"}
    response = exchange(client, created["session_id"], approval["exchange_code"])
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert set(data) == {"access_token", "refresh_token", "token_type", "user"}
    assert data["token_type"] == "bearer"
    assert data["user"] == client.get("/api/auth/me", headers=headers).json()
    assert data["user"]["application_permissions"] == {"application": ["view"]}
    assert client.get("/api/auth/me", headers=bearer(data["access_token"])).json() == data["user"]
    payload = jwt.decode(data["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "user"
    assert payload["ver"] == 1

    async def inspect(db):
        row = (
            await db.execute(
                text(
                    "SELECT exchange_code_hash, consumed_at, approved_session_version "
                    "FROM cli_auth_sessions"
                )
            )
        ).one()
        tokens = (await db.scalars(select(UserToken))).all()
        normal_user = await get_current_user(headers["Authorization"][7:], db)
        cli_user = await get_current_user(data["access_token"], db)
        assert cli_user.access_map == normal_user.access_map
        return row, tokens

    row, tokens = run_db(maker, inspect)
    assert row[0] == hashlib.sha256(approval["exchange_code"].encode()).hexdigest()
    assert row[1] is not None
    assert row[2] == 1
    assert len(tokens) == 1
    assert tokens[0].purpose == UserTokenPurpose.refresh
    assert tokens[0].token_hash == hashlib.sha256(data["refresh_token"].encode()).hexdigest()
    assert payload["cli_refresh_id"] == tokens[0].id
    secrets_issued = [VERIFIER, approval["exchange_code"], data["access_token"]]
    secrets_issued.append(data["refresh_token"])
    for action in ("auth.cli_approve", "auth.cli_exchange"):
        events = audit_rows(maker, action)
        assert len(events) == 1
        assert events[0].outcome == "success"
        assert events[0].actor_user_id == user_id
        assert events[0].target_type == "cli_auth_session"
        assert events[0].target_id == created["session_id"]
        assert all(secret not in str(events[0].details) for secret in secrets_issued)
    assert "set-cookie" not in response.headers
    assert exchange(client, created["session_id"], approval["exchange_code"]).status_code == 400
    assert [event.outcome for event in audit_rows(maker, "auth.cli_exchange")] == [
        "success",
        "failure",
    ]


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "http://127.0.0.1:8123/callback",
        "http://localhost:8123/callback?existing=a%20b",
        "http://[::1]:8123/callback",
        "http://127.0.0.1:8123/callback?x=a;state=b",
    ],
)
def test_callback_approval_encodes_code_and_state(cli_client, redirect_uri):
    client, _, headers, _, _ = cli_client
    state = "state with & and + and ="
    created = start(client, mode="callback", redirect_uri=redirect_uri, state=state)
    result = approve(client, headers, created["session_id"])
    assert set(result) == {"redirect_to"}
    target = urlsplit(result["redirect_to"])
    assert target.scheme == "http"
    assert target.netloc == urlsplit(redirect_uri).netloc
    assert target.path == urlsplit(redirect_uri).path
    params = parse_qs(target.query)
    for name, values in parse_qs(urlsplit(redirect_uri).query).items():
        assert params[name] == values
    assert params["state"] == [state]
    assert len(params["code"]) == 1
    assert exchange(client, created["session_id"], params["code"][0]).status_code == 200


def test_refresh_rotates_and_revokes_previous_cli_access(cli_client):
    client, maker, headers, user_id, _ = cli_client
    session = start(client)
    first = signed_in(client, session["session_id"], headers)
    refreshed = client.post(PREFIX + "/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    second = refreshed.json()
    assert set(second) == {"access_token", "refresh_token", "token_type", "user"}
    assert second["refresh_token"] != first["refresh_token"]
    assert "set-cookie" not in refreshed.headers
    refresh_events = audit_rows(maker, "auth.cli_refresh")
    assert [(e.outcome, e.actor_user_id, e.target_id) for e in refresh_events] == [
        ("success", user_id, str(user_id))
    ]
    replay = client.post(PREFIX + "/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    assert client.get("/api/auth/me", headers=bearer(first["access_token"])).status_code == 401
    assert client.get("/api/auth/me", headers=bearer(second["access_token"])).status_code == 200
    run_db(maker, lambda db: invalidate_all_refresh_tokens(db, user_id))
    assert client.get("/api/auth/me", headers=bearer(second["access_token"])).status_code == 401
    revoked = client.post(PREFIX + "/refresh", json={"refresh_token": second["refresh_token"]})
    assert revoked.status_code == 401
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert [e.outcome for e in audit_rows(maker, "auth.cli_refresh")] == [
        "success",
        "failure",
        "failure",
    ]


def test_cli_and_browser_refresh_share_the_user_refresh_tokens(cli_client):
    client, maker, headers, user_id, _ = cli_client
    browser_token = run_db(
        maker,
        lambda db: create_user_token(
            db,
            user_id=user_id,
            purpose=UserTokenPurpose.refresh,
            ttl_hours=24,
            invalidate_existing=False,
        ),
    )
    from_browser = client.post(PREFIX + "/refresh", json={"refresh_token": browser_token})
    assert from_browser.status_code == 200, from_browser.text
    payload = jwt.decode(
        from_browser.json()["access_token"], settings.SECRET_KEY, algorithms=["HS256"]
    )
    assert "cli_refresh_id" in payload
    cli_token = signed_in(client, start(client)["session_id"], headers)["refresh_token"]
    client.cookies.set(REFRESH_COOKIE, cli_token)
    browser = client.post("/api/auth/refresh")
    assert browser.status_code == 200, browser.text
    assert "cli_refresh_id" not in jwt.decode(
        browser.json()["access_token"], settings.SECRET_KEY, algorithms=["HS256"]
    )
    client.cookies.clear()
    assert client.post(PREFIX + "/refresh", json={"refresh_token": cli_token}).status_code == 401


def test_approval_is_once_and_authenticated(cli_client):
    client, maker, headers, user_id, _ = cli_client
    session = start(client)
    session_id = session["session_id"]
    assert client.get(PREFIX + "/sessions/" + session_id).status_code == 401
    assert client.post(PREFIX + "/approve", json={"session_id": session_id}).status_code == 401
    approve(client, headers, session_id)
    again = client.post(PREFIX + "/approve", headers=headers, json={"session_id": session_id})
    assert again.status_code == 400
    events = audit_rows(maker, "auth.cli_approve")
    assert [(e.outcome, e.actor_user_id, e.target_id) for e in events] == [
        ("success", user_id, session_id),
        ("failure", user_id, session_id),
    ]
    assert events[1].details == {"reason": "not_pending"}


def test_session_version_change_rejects_approved_code(cli_client):
    client, maker, headers, user_id, _ = cli_client
    session = start(client)
    code = approve(client, headers, session["session_id"])["exchange_code"]
    run_db(
        maker,
        lambda db: db.execute(update(User).where(User.id == user_id).values(session_version=2)),
    )
    assert exchange(client, session["session_id"], code).status_code == 400
    failure = audit_rows(maker, "auth.cli_exchange")[-1]
    assert failure.outcome == "failure"
    assert failure.details == {"reason": "inactive_or_changed_user"}
    assert run_db(maker, lambda db: db.scalars(select(UserToken))).all() == []


def test_a_new_start_deletes_expired_and_consumed_sessions(cli_client):
    client, maker, headers, _, _ = cli_client
    expired = start(client)["session_id"]
    pending = start(client)["session_id"]
    consumed = start(client)["session_id"]
    signed_in(client, consumed, headers)
    run_db(
        maker,
        lambda db: db.execute(
            update(CliAuthSession)
            .where(CliAuthSession.id == UUID(expired))
            .values(expires_at=datetime.utcnow() - timedelta(seconds=1))
        ),
    )

    async def ids(db):
        return {str(value) for value in (await db.scalars(select(CliAuthSession.id))).all()}

    assert run_db(maker, ids) == {expired, consumed, pending}
    newest = start(client)["session_id"]
    assert run_db(maker, ids) == {pending, newest}
    assert client.get(PREFIX + "/sessions/" + pending, headers=headers).status_code == 200


def test_request_code_matches_the_shared_vector():
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(RFC7636_VERIFIER.encode("ascii")).digest())
        .decode()
        .rstrip("=")
    )
    assert challenge == RFC7636_CHALLENGE
    assert cli_auth.request_code(RFC7636_CHALLENGE) == RFC7636_REQUEST_CODE
    assert cli_auth.request_code(CHALLENGE) != RFC7636_REQUEST_CODE


@pytest.mark.parametrize(
    "mode,redirect_uri", [("code", None), ("callback", "http://127.0.0.1:8123/callback")]
)
def test_session_shows_request_time_and_request_code(cli_client, mode, redirect_uri):
    client, _, headers, _, _ = cli_client
    before = datetime.utcnow().replace(microsecond=0)
    created = start(client, mode=mode, redirect_uri=redirect_uri, code_challenge=RFC7636_CHALLENGE)
    response = client.get(PREFIX + "/sessions/" + created["session_id"], headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert set(data) == SESSION_FIELDS
    assert data["request_code"] == RFC7636_REQUEST_CODE
    assert data["created_at"].endswith("Z")
    assert data["expires_at"].endswith("Z")
    requested = datetime.fromisoformat(data["created_at"][:-1])
    expires = datetime.fromisoformat(data["expires_at"][:-1])
    assert before <= requested <= datetime.utcnow()
    assert expires - requested == timedelta(minutes=10)
    assert RFC7636_CHALLENGE not in response.text


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "http://127.0.0.1:8123/callback",
        "http://localhost:8123/callback?existing=a%20b",
        "http://[::1]:8123/callback",
    ],
)
def test_deny_ends_a_callback_request_with_access_denied_and_its_state(cli_client, redirect_uri):
    client, maker, headers, user_id, _ = cli_client
    state = "state with & and + and ="
    created = start(client, mode="callback", redirect_uri=redirect_uri, state=state)
    response = deny(client, headers, created["session_id"])
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {"redirect_to"}
    target = urlsplit(response.json()["redirect_to"])
    assert (target.scheme, target.netloc, target.path) == (
        "http",
        urlsplit(redirect_uri).netloc,
        urlsplit(redirect_uri).path,
    )
    params = parse_qs(target.query, keep_blank_values=True)
    for name, values in parse_qs(urlsplit(redirect_uri).query).items():
        assert params[name] == values
    assert params["error"] == ["access_denied"]
    assert params["state"] == [state]
    assert "code" not in params
    assert stored_ids(maker) == set()
    events = audit_rows(maker, "auth.cli_deny")
    assert [(e.outcome, e.actor_user_id, e.target_type, e.target_id) for e in events] == [
        ("success", user_id, "cli_auth_session", created["session_id"])
    ]


def test_deny_ends_a_code_request_with_an_empty_answer(cli_client):
    client, maker, headers, user_id, _ = cli_client
    created = start(client)
    response = deny(client, headers, created["session_id"])
    assert response.status_code == 200, response.text
    assert response.json() == {}
    assert stored_ids(maker) == set()
    assert [(e.outcome, e.actor_user_id) for e in audit_rows(maker, "auth.cli_deny")] == [
        ("success", user_id)
    ]


@pytest.mark.parametrize("mode", ["code", "callback"])
def test_a_denied_request_answers_as_a_missing_one(cli_client, mode):
    client, _, headers, _, _ = cli_client
    redirect_uri = "http://127.0.0.1:8123/callback" if mode == "callback" else None
    session_id = start(client, mode=mode, redirect_uri=redirect_uri)["session_id"]
    assert deny(client, headers, session_id).status_code == 200
    assert client.get(PREFIX + "/sessions/" + session_id, headers=headers).status_code == 400
    again = client.post(PREFIX + "/approve", headers=headers, json={"session_id": session_id})
    assert again.status_code == 400
    assert exchange(client, session_id, "any-code").status_code == 400
    assert deny(client, headers, session_id).status_code == 400
