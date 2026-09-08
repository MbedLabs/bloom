import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_email, unique_suffix

"""Deleting a user must actually delete the user."""


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_user(api_client, headers, role="external"):
    created = api_client.post(
        "/api/users",
        headers=headers,
        json={
            "email": unique_email("deleteme"),
            "full_name": "Delete Me",
            "password": "a-sufficiently-long-passphrase",
            "role": role,
        },
    )
    assert created.status_code in (200, 201), created.text
    return created.json()["id"]


def _user_exists(api_client, headers, user_id) -> bool:
    listed = api_client.get("/api/users", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    rows = body["items"] if isinstance(body, dict) else body
    return any(row["id"] == user_id for row in rows)


def test_deleting_a_plain_user_removes_it(api_client: TestClient):
    headers = _admin_headers(api_client)
    user_id = _create_user(api_client, headers)

    deleted = api_client.delete(f"/api/users/{user_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    assert not _user_exists(api_client, headers, user_id)


def test_deleting_a_project_member_removes_it(api_client: TestClient):
    """The case that fails in production. ProjectMembership.user_id is NOT NULL
    and was never cleared, so every user actually assigned to a project - which
    is every user who can do anything - was undeletable, while the UI was told
    the deletion had worked.
    """
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Member Del {suffix}")["id"]
    user_id = _create_user(api_client, headers)

    added = api_client.post(
        f"/api/projects/{project_id}/members",
        headers=headers,
        json={"user_id": user_id, "role": "external"},
    )
    assert added.status_code in (200, 201), added.text

    deleted = api_client.delete(f"/api/users/{user_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    # The assertion that actually caught this: a 204 alone proved nothing.
    assert not _user_exists(
        api_client, headers, user_id
    ), "the API reported success but the user is still there"
