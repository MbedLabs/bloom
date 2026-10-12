"""User promotion endpoint rules: seed admin promotes, non-seed admin rejected."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import unique_email


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _login_headers(api_client: TestClient, email: str, password: str) -> dict[str, str]:
    login = api_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_user(
    api_client: TestClient, headers: dict[str, str], role: str, email: str | None = None
) -> tuple[int, str]:
    email = email or unique_email("user")
    password = "a-sufficiently-long-passphrase"
    created = api_client.post(
        "/api/users",
        headers=headers,
        json={
            "email": email,
            "full_name": "Test User",
            "password": password,
            "role": role,
        },
    )
    assert created.status_code in (200, 201), created.text
    return created.json()["id"], password


def test_seed_admin_can_promote_maintainer_to_admin(api_client: TestClient):
    seed_headers = _admin_headers(api_client)
    user_id, _ = _create_user(api_client, seed_headers, role="maintainer")

    patch_resp = api_client.patch(
        f"/api/users/{user_id}",
        headers=seed_headers,
        json={"role": "admin"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["role"] == "admin"


def test_non_seed_admin_cannot_promote_user_to_admin(api_client: TestClient):
    seed_headers = _admin_headers(api_client)
    other_admin_id, other_password = _create_user(
        api_client, seed_headers, role="admin", email=unique_email("otheradmin")
    )
    target_id, _ = _create_user(api_client, seed_headers, role="maintainer")

    other_email = api_client.get(f"/api/users/{other_admin_id}", headers=seed_headers).json()[
        "email"
    ]
    other_headers = _login_headers(api_client, other_email, other_password)

    patch_resp = api_client.patch(
        f"/api/users/{target_id}",
        headers=other_headers,
        json={"role": "admin"},
    )
    assert patch_resp.status_code == 403, patch_resp.text
    assert (
        "Only the initial administrator can promote users to admin" in patch_resp.json()["detail"]
    )


def test_admin_cannot_be_demoted(api_client: TestClient):
    seed_headers = _admin_headers(api_client)
    admin_id, _ = _create_user(api_client, seed_headers, role="admin", email=unique_email("admin2"))

    patch_resp = api_client.patch(
        f"/api/users/{admin_id}",
        headers=seed_headers,
        json={"role": "maintainer"},
    )
    assert patch_resp.status_code == 400, patch_resp.text
    assert "Admin role cannot be changed" in patch_resp.json()["detail"]
