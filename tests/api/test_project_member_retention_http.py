"""Removing project access preserves the account and its project contributions."""

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models import (
    ArtefactActivity,
    ArtefactComment,
    Document,
    DocumentAttachment,
    Project,
    Requirement,
)
from app.models.groups import Group, Policy
from app.models.user import User, UserRole
from app.models.workflow import ArtefactRevision, ArtefactWorkflow


@pytest_asyncio.fixture
async def retention_http():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        db.add_all(
            [
                Project(id=1, name="Demo", prefix="PRJ"),
                Project(id=2, name="ABC", prefix="ABC"),
                User(
                    id=1,
                    email="admin@example.com",
                    full_name="Admin",
                    hashed_password="x",
                    role=UserRole.admin,
                ),
                User(
                    id=2,
                    email="author@example.com",
                    full_name="Author",
                    hashed_password="x",
                    role=UserRole.maintainer,
                ),
            ]
        )
        await db.flush()

        async def session():
            yield db
            await db.flush()

        app.dependency_overrides[get_db] = session
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield db, client
        finally:
            app.dependency_overrides.pop(get_db, None)
            await db.rollback()
    await engine.dispose()


def headers(user):
    return {
        "Authorization": "Bearer "
        + create_access_token({"sub": str(user.id), "type": "user", "ver": user.session_version})
    }


async def retained_rows(db):
    """Compare stored values, including all user references, across access changes."""
    excluded = {"audit_events", "project_access", "project_access_policies"}
    return {
        table.name: (await db.execute(select(table).order_by(*table.primary_key.columns))).all()
        for table in Base.metadata.sorted_tables
        if table.name not in excluded
    }


@pytest.mark.parametrize("assignment", ["bundle", "individual"])
async def test_remove_and_readd_retains_uid_content_and_other_project(retention_http, assignment):
    db, client = retention_http
    admin, author = headers(await db.get(User, 1)), headers(await db.get(User, 2))
    policy = Policy(
        name="Project content",
        permissions={"REQ": ["view", "create", "edit"], "RPT": ["view", "create", "edit"]},
        type_tags={"REQ": {"all": True}, "RPT": {"all": True}},
    )
    group = Group(name="Contributors", policies=[policy])
    db.add(group)
    await db.flush()

    async def assign(project_id):
        if assignment == "bundle":
            response = await client.post(
                f"/api/groups/{group.id}/assignments",
                headers=admin,
                json={"project_id": project_id, "user_ids": [2]},
            )
            assert response.status_code == 200, response.text
            return response.json()[0]
        response = await client.post(
            f"/api/projects/{project_id}/members",
            headers=admin,
            json={"user_id": 2, "policy_ids": [policy.id]},
        )
        assert response.status_code == 201, response.text
        return response.json()

    membership = await assign(1)
    other_membership = await assign(2)
    requirement = Requirement(
        project_id=1, req_id="PRJ-REQ-001", title="Authored content", created_by_id=2, reviewer_id=2
    )
    document = Document(
        project_id=1, doc_id="PRJ-RPT-001", doc_type="RPT", title="Authored report", created_by_id=2
    )
    db.add_all([requirement, document])
    await db.flush()
    workflow = ArtefactWorkflow(
        project_id=1,
        artefact_type="requirement",
        artefact_id=requirement.id,
        revision_creator_id=2,
        reviewer_id=2,
    )
    db.add(workflow)
    await db.flush()
    db.add_all(
        [
            ArtefactComment(
                artefact_type="requirement",
                artefact_id=requirement.id,
                author_name="Author",
                author_user_id=2,
                body="Recorded review comment",
            ),
            ArtefactActivity(
                artefact_type="requirement",
                artefact_id=requirement.id,
                event_type="created",
                summary="Author created the requirement",
                actor_user_id=2,
            ),
            ArtefactRevision(
                workflow_id=workflow.id,
                revision_number=1,
                content_snapshot={"title": "Preserved earlier revision"},
                content_hash="a" * 64,
                reviewed_by_id=2,
                approved_by_id=1,
            ),
            DocumentAttachment(
                document_id=document.id,
                filename="retained.txt",
                original_filename="retained.txt",
                storage_path="retained.txt",
                content_type="text/plain",
                size_bytes=4,
                sha256="b" * 64,
                uploaded_by_id=2,
            ),
        ]
    )
    await db.flush()
    before = await retained_rows(db)
    assert (await client.get("/api/projects/1", headers=author)).status_code == 200
    assert (
        await client.get(f"/api/requirements/{requirement.id}", headers=author)
    ).status_code == 200
    response = await client.delete(f"/api/projects/1/members/{membership['id']}", headers=admin)
    assert response.status_code == 204, response.text
    assert (await client.get("/api/projects/1", headers=author)).status_code == 403
    assert (
        await client.get(f"/api/requirements/{requirement.id}", headers=author)
    ).status_code == 404
    assert (await client.get("/api/projects/2", headers=author)).status_code == 200
    assert (await client.get("/api/projects/2/members", headers=admin)).json() == [other_membership]
    assert await retained_rows(db) == before
    options = (await client.get("/api/groups/assignment-options", headers=admin)).json()
    assert (
        next(person for person in options["users"] if person["email"] == "author@example.com")["id"]
        == 2
    )
    restored = await assign(1)
    assert restored["user_id"] == membership["user_id"] == 2
    assert (await client.get("/api/projects/1", headers=author)).status_code == 200
    content = await client.get(f"/api/requirements/{requirement.id}", headers=author)
    assert content.status_code == 200, content.text
    assert content.json()["title"] == "Authored content"
    assert (await client.get(f"/api/documents/{document.id}/attachments", headers=author)).json()[
        0
    ]["uploaded_by_id"] == 2
    assert await retained_rows(db) == before
