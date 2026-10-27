"""A Vision is approved, corrected and revised like a Specification, and hosts and takes tags."""

import io

from sqlalchemy import select
from starlette.datastructures import UploadFile

from app.api.import_service import import_markdown
from app.core.md_import import normalize_type
from app.models import ArtefactLink, ChangeRequest, Document, Requirement, User
from app.services.tag_links import sync_tag_links
from tests.api.test_document_workflow_http import workflow_http  # noqa: F401


async def _approve(client, current, users, path):
    response = await client.put(
        path + "/workflow/assignees", json={"reviewer_id": 2, "approver_id": 3}
    )
    assert response.status_code == 200, response.text
    current[0] = users[0]
    response = await client.post(path + "/requests", json={"kind": "review"})
    assert response.status_code == 201, response.text
    current[0] = users[1]
    response = await client.post(path + "/comments", json={"body": "Reviewed the vision"})
    assert response.status_code == 201, response.text
    response = await client.post(path + "/requests", json={"kind": "approval"})
    assert response.status_code == 201, response.text
    current[0] = users[2]
    response = await client.post(path + "/sign-off", json={"step": "approve"})
    assert response.status_code == 200, response.text
    current[0] = users[0]


async def test_a_vision_is_approved_corrected_and_revised_through_a_change(workflow_http):
    db, client, current, users = workflow_http
    vision = Document(
        project_id=1,
        doc_id="PRJ-VIS-001",
        doc_type="VIS",
        title="Idea",
        status="Draft",
        version="1",
        created_by_id=1,
    )
    db.add(vision)
    await db.flush()
    path = f"/api/artefacts/document/{vision.id}"
    state = (await client.get(path + "/workflow")).json()
    assert state["controlled"] is True
    assert state["phase"] == "Draft"
    assert state["revisions"] == []

    await _approve(client, current, users, path)
    state = (await client.get(path + "/workflow")).json()
    assert state["phase"] == "Approved"
    assert [item["revision_number"] for item in state["revisions"]] == [1]

    response = await client.patch(f"/api/documents/{vision.id}", json={"title": "Corrected"})
    assert response.status_code == 200, response.text
    state = (await client.get(path + "/workflow")).json()
    assert (state["phase"], state["revision_number"]) == ("Draft", 1)
    assert [item["revision_number"] for item in state["revisions"]] == [1]

    change = ChangeRequest(
        project_id=1, change_id="PRJ-CHG-001", title="Next vision", status="Approved"
    )
    db.add(change)
    await db.flush()
    link = await client.post(
        "/api/links",
        json={
            "project_id": 1,
            "source_type": "CHG",
            "source_id": change.id,
            "target_type": "VIS",
            "target_id": vision.id,
            "role": "impacts",
        },
    )
    assert link.status_code == 201, link.text
    response = await client.patch(f"/api/documents/{vision.id}", json={"title": "Revised"})
    assert response.status_code == 200, response.text
    state = (await client.get(path + "/workflow")).json()
    assert (state["phase"], state["revision_number"]) == ("Draft", 2)
    assert state["authorizing_change"]["id"] == change.id
    assert vision.version == "2"


async def test_a_vision_tags_any_kind_and_is_tagged_by_any_tag_host(workflow_http):
    db, _, _, _ = workflow_http
    vision = Document(project_id=1, doc_id="PRJ-VIS-001", doc_type="VIS", title="Vision")
    requirement = Requirement(project_id=1, req_id="PRJ-REQ-001", title="Requirement")
    db.add_all([vision, requirement])
    await db.flush()
    admin = await db.get(User, 1)

    def mention(kind, identifier):
        return {
            "type": "mention",
            "attrs": {"id": f"{kind}:{identifier}", "mentionSuggestionChar": "#"},
        }

    created = await sync_tag_links(
        db,
        project_id=1,
        source_type="VIS",
        source_id=vision.id,
        content_json=mention("REQ", requirement.id),
        user=admin,
    )
    assert created == 1
    created = await sync_tag_links(
        db,
        project_id=1,
        source_type="REQ",
        source_id=requirement.id,
        content_json=mention("VIS", vision.id),
        user=admin,
    )
    assert created == 1
    await db.flush()
    links = (await db.execute(select(ArtefactLink))).scalars().all()
    assert sorted((link.source_type, link.target_type, link.role) for link in links) == [
        ("REQ", "VIS", "references"),
        ("VIS", "REQ", "references"),
    ]


async def test_markdown_import_files_vis_and_vision_sections_as_visions(workflow_http):
    db, _, _, users = workflow_http
    assert normalize_type("vis") == "VIS"
    assert normalize_type("Vision") == "VIS"
    await import_markdown(
        project_id=1,
        default_type=None,
        file=UploadFile(io.BytesIO(b"## [VIS] North star\nWhere the product goes\n")),
        collision_actions=None,
        db=db,
        current_user=users[0],
    )
    visions = (await db.execute(select(Document).where(Document.doc_type == "VIS"))).scalars().all()
    assert [(vision.doc_id, vision.title, vision.status) for vision in visions] == [
        ("PRJ-VIS-001", "North star", "Draft")
    ]
