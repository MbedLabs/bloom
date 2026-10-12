"""Current pictures accompany identities through existing authenticated read scopes."""

import asyncio
import base64
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api import (
    access_requests,
    artefacts,
    audit,
    auth,
    groups,
    notifications,
    project_memberships,
    users,
)
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models import Project, Requirement, User
from app.models.access_request import AccessRequest
from app.models.audit import AuditEvent
from app.models.user import UserRole
from tests.access_fixtures import project_access_fixture


@pytest.fixture
def identity_client():
    """Real authenticated routes with distinct pictures and isolated project membership."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with maker() as db:
            people = []
            for index, role in enumerate([UserRole.admin, UserRole.maintainer, UserRole.external]):
                data = io.BytesIO()
                Image.new("RGB", (32, 32), ["purple", "green", "blue"][index]).save(data, "PNG")
                person = User(
                    email=f"identity-{index}@example.com",
                    full_name=f"Person {index}",
                    role=role,
                    hashed_password="unused",
                    profile_picture=data.getvalue(),
                )
                people.append(person)
            db.add_all(people)
            project = Project(name="Project", prefix="PRJ")
            hidden = Project(name="Separate project", prefix="OTH")
            db.add_all([project, hidden])
            await db.flush()
            db.add(
                project_access_fixture(
                    user_id=people[1].id,
                    project_id=project.id,
                    permissions={"REQ": ["view", "review"]},
                )
            )
            requirement = Requirement(
                project_id=project.id,
                req_id="PRJ-REQ-001",
                title="Requirement",
                status="Draft",
                visibility="internal",
                req_type="Functional",
                req_origin="Internal",
                priority="Medium",
                reviewer_id=people[1].id,
                approver_id=people[0].id,
            )
            db.add(requirement)
            db.add(
                AuditEvent(actor_user_id=people[1].id, actor_type="user", action="identity.read")
            )
            db.add(
                AccessRequest(
                    user_id=people[1].id,
                    resource_type="project",
                    resource_ref="PRJ",
                    project_prefix="PRJ",
                )
            )
            await db.commit()
            headers = [
                {
                    "Authorization": "Bearer "
                    + create_access_token({"sub": str(person.id), "type": "user", "ver": 1})
                }
                for person in people
            ]
            return headers, project.id, hidden.id, requirement.id

    async def database():
        async with maker() as db:
            yield db
            await db.commit()

    api = FastAPI()
    for name, router in [
        ("auth", auth.router),
        ("users", users.router),
        ("groups", groups.router),
        ("projects", project_memberships.router),
        ("artefacts", artefacts.router),
        ("audit", audit.router),
        ("notifications", notifications.router),
        ("access-requests", access_requests.router),
    ]:
        api.include_router(router, prefix=f"/api/{name}")
    api.dependency_overrides[get_db] = database
    seeded = asyncio.run(seed())
    with TestClient(api) as client:
        yield client, *seeded
    asyncio.run(engine.dispose())


def png(url):
    """Decode the supported PNG data URL returned with an identity."""
    assert url.startswith("data:image/png;base64,")
    return base64.b64decode(url.split(",", 1)[1])


def test_directory_and_mentions_return_each_persons_current_picture(identity_client):
    client, (admin, member, outsider), project_id, hidden_id, _ = identity_client
    people = client.get("/api/users", headers=admin).json()
    pictures = {person["id"]: png(person["profile_picture_url"]) for person in people}
    assert len(set(pictures.values())) == 3
    mentionable = client.get(
        "/api/users/mentionable", params={"project_id": project_id}, headers=member
    )
    assert mentionable.status_code == 200
    assert len(mentionable.json()) == 2
    for person in mentionable.json():
        assert png(person["profile_picture_url"]) == pictures[person["id"]]
    assert client.get("/api/users", headers=member).status_code == 403
    assert client.get(
        "/api/users/mentionable", params={"project_id": hidden_id}, headers=member
    ).status_code in {403, 404}
    assert client.get(
        "/api/users/mentionable", params={"project_id": project_id}, headers=outsider
    ).status_code in {403, 404}
    assert client.get("/api/users").status_code == 401


def test_roster_options_and_audit_retain_the_same_person_picture(identity_client):
    client, (admin, _, _), project_id, _, _ = identity_client
    options = client.get("/api/groups/assignment-options", headers=admin).json()["users"]
    pictures = {person["id"]: person["profile_picture_url"] for person in options}
    roster = client.get(f"/api/projects/{project_id}/members", headers=admin).json()
    assert roster[0]["profile_picture_url"] == pictures[roster[0]["user_id"]]
    actor = client.get("/api/audit", headers=admin).json()["items"][0]
    assert actor["actor_profile_picture_url"] == pictures[actor["actor_user_id"]]


def test_new_comment_uses_authenticated_author_and_current_picture(identity_client):
    client, (admin, member, outsider), _, _, requirement_id = identity_client
    url = f"/api/artefacts/requirement/{requirement_id}/comments"
    me = client.get("/api/auth/me", headers=member).json()
    assert (
        client.post(
            url, headers=member, json={"body": "Review note", "author_user_id": 999}
        ).status_code
        == 422
    )
    created = client.post(url, headers=member, json={"body": "Review note"})
    assert created.status_code == 201, created.text
    assert created.json()["author_user_id"] == me["id"]
    assert created.json()["author_profile_picture_url"] == me["profile_picture_url"]
    assert (
        client.put("/api/auth/me", headers=member, json={"full_name": "Changed Name"}).status_code
        == 200
    )
    stored = client.get(url, headers=admin).json()[0]
    assert stored["author_user_id"] == me["id"]
    assert stored["author_profile_picture_url"] == me["profile_picture_url"]
    assert client.get(url, headers=outsider).status_code in {403, 404}
    assert client.delete("/api/auth/me/picture", headers=member).status_code == 200
    assert client.get(url, headers=admin).json()[0]["author_profile_picture_url"] is None


def test_directory_picture_changes_on_replace_and_remove(identity_client):
    client, (admin, member, _), project_id, _, _ = identity_client
    original = client.get(
        "/api/users/mentionable", params={"project_id": project_id}, headers=member
    ).json()
    own_id = client.get("/api/auth/me", headers=member).json()["id"]
    previous = next(person for person in original if person["id"] == own_id)["profile_picture_url"]
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, "PNG")
    saved = client.put(
        "/api/auth/me/picture",
        headers=member,
        files={"file": ("photo.png", buffer.getvalue(), "image/png")},
    )
    assert saved.status_code == 200
    assert saved.json()["profile_picture_url"] != previous
    directory = client.get("/api/users", headers=admin).json()
    assert (
        next(person for person in directory if person["id"] == own_id)["profile_picture_url"]
        == saved.json()["profile_picture_url"]
    )
    assert client.delete("/api/auth/me/picture", headers=member).status_code == 200
    assert (
        next(
            person
            for person in client.get("/api/users", headers=admin).json()
            if person["id"] == own_id
        )["profile_picture_url"]
        is None
    )


def test_access_request_picture_stays_with_requester_and_existing_authority(identity_client):
    """Requester pictures use the existing request list authority and current account data."""
    client, headers, _project, _hidden, _requirement = identity_client
    admin, member, outsider = headers
    person = client.get("/api/auth/me", headers=member).json()
    request = client.get("/api/access-requests", headers=admin).json()[0]
    assert request["requester_name"] == person["full_name"]
    assert request["requester_profile_picture_url"] == person["profile_picture_url"]
    assert client.get("/api/access-requests", headers=member).status_code == 403
    assert client.get("/api/access-requests", headers=outsider).status_code == 403
    assert client.delete("/api/auth/me/picture", headers=member).status_code == 200
    assert (
        client.get("/api/access-requests", headers=admin).json()[0]["requester_profile_picture_url"]
        is None
    )


def test_new_activity_and_notification_identify_the_real_actor(identity_client):
    """Current actor pictures accompany guarded activity and recipient notifications."""
    client, (admin, member, outsider), _, _, requirement_id = identity_client
    person = client.get("/api/auth/me", headers=member).json()
    base = f"/api/artefacts/requirement/{requirement_id}"
    assert (
        client.post(base + "/comments", headers=member, json={"body": "Review note"}).status_code
        == 201
    )
    event = client.get(base + "/activity", headers=admin).json()[0]
    assert event["actor_user_id"] == person["id"]
    assert event["actor_name"] == person["full_name"]
    assert event["actor_profile_picture_url"] == person["profile_picture_url"]
    notice = client.get("/api/notifications", headers=admin).json()["items"][0]
    assert notice["actor_user_id"] == person["id"]
    assert notice["actor_profile_picture_url"] == person["profile_picture_url"]
    assert client.get("/api/notifications", headers=outsider).json()["items"] == []
    assert (
        client.post(f"/api/notifications/{notice['id']}/read", headers=outsider).status_code == 404
    )
    assert client.get(base + "/activity", headers=outsider).status_code in {403, 404}
    assert (
        client.put("/api/auth/me", headers=member, json={"full_name": "Changed Actor"}).status_code
        == 200
    )
    assert client.get(base + "/activity", headers=admin).json()[0]["actor_name"] == "Changed Actor"
    assert client.delete("/api/auth/me/picture", headers=member).status_code == 200
    assert (
        client.get(base + "/activity", headers=admin).json()[0]["actor_profile_picture_url"] is None
    )
    assert (
        client.get("/api/notifications", headers=admin).json()["items"][0][
            "actor_profile_picture_url"
        ]
        is None
    )
    assert (
        client.post(f"/api/notifications/{notice['id']}/read", headers=admin).json()[
            "actor_profile_picture_url"
        ]
        is None
    )
