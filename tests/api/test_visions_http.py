"""Visions: the VIS document kind, its built-in access, its links and its baseline section."""

from fastapi.testclient import TestClient

from tests.api.test_group_permissions_http import _policy_user
from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.conftest import create_project, unique_name


def _built_in(api_client, admin, name) -> int:
    policies = api_client.get("/api/policies", headers=admin).json()
    return next(
        policy["id"] for policy in policies if policy["is_default"] and policy["name"] == name
    )


def _holder(api_client, admin, project, *names, return_user=False):
    """A maintainer holding the named built-in policies on the project, with their headers."""
    user = _create_user(api_client, admin, role="maintainer")
    for name in names:
        group = _create_group(api_client, admin, policy_id=_built_in(api_client, admin, name))
        granted = api_client.post(
            f"/api/groups/{group['id']}/grants", headers=admin, json={"project_id": project}
        )
        assert granted.status_code == 201, granted.text
        added = api_client.post(
            f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
        )
        assert added.status_code == 201, added.text
    headers = _headers_for(api_client, user["email"])
    return (user, headers) if return_user else headers


def _document(api_client, headers, project, doc_type, visibility="internal"):
    return api_client.post(
        f"/api/projects/{project}/documents",
        headers=headers,
        json={
            "project_id": project,
            "doc_type": doc_type,
            "title": unique_name(doc_type),
            "visibility": visibility,
        },
    )


def _prefix(api_client, admin, project) -> str:
    return api_client.get(f"/api/projects/{project}", headers=admin).json()["prefix"]


def test_the_product_owners_group_holds_the_visions_policy(api_client: TestClient):
    admin = _admin_headers(api_client)
    visions = _built_in(api_client, admin, "Visions")
    groups = {group["name"]: group for group in api_client.get("/api/groups", headers=admin).json()}
    assert visions in groups["Product Owners"]["policy_ids"]
    for name in ("Developers", "Testers", "Administrators", "Customers"):
        assert visions not in groups[name]["policy_ids"]


def test_a_vision_is_created_as_draft_with_its_own_id_and_listed_as_visions(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Visions")["id"]
    prefix = _prefix(api_client, admin, project)
    author = _holder(api_client, admin, project, "Visions")

    created = _document(api_client, author, project, "VIS")
    assert created.status_code == 201, created.text
    vision = created.json()
    assert vision["doc_id"] == f"{prefix}-VIS-001"
    assert vision["doc_type"] == "VIS"
    assert vision["status"] == "Draft"
    edited = api_client.patch(
        f"/api/documents/{vision['id']}", headers=author, json={"title": "Edited vision"}
    )
    assert edited.status_code == 200, edited.text

    listed = api_client.get(f"/api/projects/{prefix}/docs", headers=author, params={"type": "VIS"})
    assert listed.status_code == 200, listed.text
    assert [item["doc_id"] for item in listed.json()["items"]] == [vision["doc_id"]]
    detail = api_client.get(
        f"/api/projects/{prefix}/docs/visions/{vision['doc_id']}", headers=author
    )
    assert detail.status_code == 200, detail.text
    assert {"edit", "approve"} <= set(detail.json()["allowed_actions"])


def test_built_in_read_and_review_cover_visions_and_editable_spec_rights_do_not(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Vision readers")["id"]
    prefix = _prefix(api_client, admin, project)
    internal = _document(api_client, admin, project, "VIS").json()
    customer = _document(api_client, admin, project, "VIS", visibility="customer").json()

    reader = _holder(api_client, admin, project, "Read Internal")
    assert api_client.get(f"/api/documents/{internal['id']}", headers=reader).status_code == 200
    denied = api_client.patch(
        f"/api/documents/{internal['id']}", headers=reader, json={"title": "Not allowed"}
    )
    assert denied.status_code == 403, denied.text

    reviewer = _holder(api_client, admin, project, "Read Internal", "Review Internal")
    detail = api_client.get(
        f"/api/projects/{prefix}/docs/visions/{internal['doc_id']}", headers=reviewer
    )
    assert detail.status_code == 200, detail.text
    assert "review" in detail.json()["allowed_actions"]

    customer_reader = _holder(api_client, admin, project, "Read Customer")
    listed = api_client.get(
        f"/api/projects/{prefix}/docs", headers=customer_reader, params={"type": "VIS"}
    )
    assert listed.status_code == 200, listed.text
    assert [item["doc_id"] for item in listed.json()["items"]] == [customer["doc_id"]]

    spec_only = _policy_user(api_client, admin, {"SPEC": ["view"]}, project)
    listed = api_client.get(
        f"/api/projects/{prefix}/docs", headers=spec_only, params={"type": "VIS"}
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"] == []
    assert api_client.get(f"/api/documents/{internal['id']}", headers=spec_only).status_code in {
        403,
        404,
    }


def test_vision_links_follow_their_rules(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Vision links")["id"]
    vision = _document(api_client, admin, project, "VIS").json()["id"]
    spec = _document(api_client, admin, project, "SPEC").json()["id"]
    standard = _document(api_client, admin, project, "STD").json()["id"]
    created = {
        kind: api_client.post(
            f"/api/{kind}", headers=admin, json={"project_id": project, "title": unique_name(kind)}
        ).json()["id"]
        for kind in ("requirements", "changes", "risks", "designs")
    }

    def link(source_type, source_id, target_type, target_id, role):
        return api_client.post(
            "/api/links",
            headers=admin,
            json={
                "project_id": project,
                "source_type": source_type,
                "source_id": source_id,
                "target_type": target_type,
                "target_id": target_id,
                "role": role,
            },
        )

    for source_type, source_id, target_type, target_id, role in [
        ("REQ", created["requirements"], "VIS", vision, "derives_from"),
        ("SPEC", spec, "VIS", vision, "refines"),
        ("CHG", created["changes"], "VIS", vision, "impacts"),
        ("RSK", created["risks"], "VIS", vision, "impacts"),
        ("VIS", vision, "STD", standard, "references"),
    ]:
        response = link(source_type, source_id, target_type, target_id, role)
        assert response.status_code == 201, (source_type, role, response.text)
    for source_type, source_id, target_type, target_id, role in [
        ("DES", created["designs"], "VIS", vision, "satisfies"),
        ("VIS", vision, "REQ", created["requirements"], "derives_from"),
        ("RSK", created["risks"], "VIS", vision, "mitigates"),
    ]:
        response = link(source_type, source_id, target_type, target_id, role)
        assert response.status_code in {400, 422}, (source_type, role, response.text)


def test_a_baseline_keeps_documents_and_visions_in_separate_sections(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Vision baseline")["id"]
    spec = _document(api_client, admin, project, "SPEC").json()
    vision = _document(api_client, admin, project, "VIS").json()
    baseline = api_client.post(
        "/api/baselines", headers=admin, json={"project_id": project, "name": unique_name("bl")}
    )
    assert baseline.status_code == 201, baseline.text
    snapshot = baseline.json()["snapshot"]
    assert snapshot["documents"] == {"count": 1, "titles": [spec["title"]]}
    assert snapshot["visions"] == {"count": 1, "ids": [vision["doc_id"]]}

    released_kinds = _policy_user(
        api_client,
        admin,
        {code: ["view"] for code in ("SPEC", "PRT", "RPT", "STD", "baseline")},
        project,
    )
    seen = api_client.get(f"/api/baselines/{baseline.json()['id']}", headers=released_kinds)
    assert set(seen.json()["snapshot"]) == {"documents"}
    vision_reader = _policy_user(
        api_client, admin, {"VIS": ["view"], "baseline": ["view"]}, project
    )
    seen = api_client.get(f"/api/baselines/{baseline.json()['id']}", headers=vision_reader)
    assert set(seen.json()["snapshot"]) == {"visions"}


RELEASED_MAINTAINER_SET = (
    "Requirements",
    "Specifications",
    "Standards",
    "Designs",
    "Risks",
    "Change Requests",
    "Concepts",
    "Test Cases",
    "Suites",
    "Campaigns",
    "Defects",
    "Protocols",
    "Reports",
    "Baselines",
    "Parameters",
    "Traceability",
    "Project Management",
)


def test_a_product_owner_and_a_released_maintainer_entry_create_and_edit_visions(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Vision authors")["id"]
    groups = {group["name"]: group for group in api_client.get("/api/groups", headers=admin).json()}
    assignments = {
        "product owner": {"policy_group_id": groups["Product Owners"]["id"]},
        "released maintainer": {
            "policy_ids": [
                _built_in(api_client, admin, name) for name in (*RELEASED_MAINTAINER_SET, "Visions")
            ]
        },
    }
    for who, assignment in assignments.items():
        user = _create_user(api_client, admin, role="maintainer")
        member = api_client.post(
            f"/api/projects/{project}/members",
            headers=admin,
            json={"user_id": user["id"], **assignment},
        )
        assert member.status_code == 201, (who, member.text)
        headers = _headers_for(api_client, user["email"])
        created = _document(api_client, headers, project, "VIS")
        assert created.status_code == 201, (who, created.text)
        edited = api_client.patch(
            f"/api/documents/{created.json()['id']}", headers=headers, json={"title": who}
        )
        assert edited.status_code == 200, (who, edited.text)


def test_a_review_internal_holder_reviews_a_vision(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Vision review")["id"]
    author, author_headers = _holder(api_client, admin, project, "Visions", return_user=True)
    reviewer, reviewer_headers = _holder(
        api_client, admin, project, "Read Internal", "Review Internal", return_user=True
    )
    approver, _ = _holder(api_client, admin, project, "Visions", return_user=True)
    vision = _document(api_client, author_headers, project, "VIS").json()["id"]
    path = f"/api/artefacts/document/{vision}"

    assigned = api_client.put(
        path + "/workflow/assignees",
        headers=author_headers,
        json={"reviewer_id": reviewer["id"], "approver_id": approver["id"]},
    )
    assert assigned.status_code == 200, assigned.text
    requested = api_client.post(path + "/requests", headers=author_headers, json={"kind": "review"})
    assert requested.status_code == 201, requested.text
    commented = api_client.post(
        path + "/comments", headers=reviewer_headers, json={"body": "Reviewed the vision"}
    )
    assert commented.status_code == 201, commented.text
    handed_on = api_client.post(
        path + "/requests", headers=reviewer_headers, json={"kind": "approval"}
    )
    assert handed_on.status_code == 201, handed_on.text
