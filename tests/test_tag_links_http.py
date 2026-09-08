"""A tag written in a document body becomes a references link."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_suffix


def _admin_headers(api_client: TestClient) -> dict[str, str]:
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _body_tagging(doc_type: str, artefact_id: int) -> dict:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "mention",
                        "attrs": {
                            "id": f"{doc_type}:{artefact_id}",
                            "label": "TAGGED",
                            "mentionSuggestionChar": "#",
                        },
                    }
                ],
            }
        ],
    }


def _links(api_client, headers, project_id, **params):
    response = api_client.get(
        "/api/links",
        headers=headers,
        params={"project_id": project_id, **params},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_tagging_a_requirement_inside_another_creates_a_references_link(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Tag {suffix}")["id"]

    target = api_client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        json={"project_id": project_id, "title": f"Target {suffix}", "doc_type": "SPEC"},
    )
    assert target.status_code in (200, 201), target.text
    target_id = target.json()["id"]

    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Source {suffix}",
            "content_json": _body_tagging("SPEC", target_id),
        },
    )
    assert source.status_code in (200, 201), source.text
    source_id = source.json()["id"]

    links = _links(api_client, headers, project_id, source_type="REQ", source_id=source_id)
    assert [(l["target_type"], l["target_id"], l["role"]) for l in links] == [
        ("SPEC", target_id, "references")
    ]


def test_the_tag_is_readable_as_a_backlink(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Backlink {suffix}")["id"]

    target = api_client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        json={"project_id": project_id, "title": f"Target {suffix}", "doc_type": "SPEC"},
    ).json()

    api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Source {suffix}",
            "content_json": _body_tagging("SPEC", target["id"]),
        },
    )

    incoming = _links(api_client, headers, project_id, target_type="SPEC", target_id=target["id"])
    assert len(incoming) == 1
    assert incoming[0]["role"] == "references"


def test_tagging_the_same_artefact_twice_creates_one_link(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Twice {suffix}")["id"]

    target = api_client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        json={"project_id": project_id, "title": f"Target {suffix}", "doc_type": "SPEC"},
    ).json()
    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Source {suffix}",
            "content_json": _body_tagging("SPEC", target["id"]),
        },
    ).json()

    updated = api_client.patch(
        f"/api/requirements/{source['id']}",
        headers=headers,
        json={"content_json": _body_tagging("SPEC", target["id"])},
    )
    assert updated.status_code == 200, updated.text

    links = _links(api_client, headers, project_id, source_type="REQ", source_id=source["id"])
    assert len(links) == 1


def test_a_document_tagging_itself_creates_nothing(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Self {suffix}")["id"]

    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Source {suffix}"},
    ).json()

    updated = api_client.patch(
        f"/api/requirements/{source['id']}",
        headers=headers,
        json={"content_json": _body_tagging("REQ", source["id"])},
    )
    assert updated.status_code == 200, updated.text

    links = _links(api_client, headers, project_id, source_type="REQ", source_id=source["id"])
    assert links == []


def test_a_tag_at_an_unknown_type_creates_nothing(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Unknown {suffix}")["id"]

    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Source {suffix}",
            "content_json": _body_tagging("NOPE", 1),
        },
    ).json()

    links = _links(api_client, headers, project_id, source_type="REQ", source_id=source["id"])
    assert links == []


def test_a_parameter_mention_is_not_a_tag(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Parameter {suffix}")["id"]

    body = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "mention",
                        "attrs": {"id": "7", "label": "MAX_TEMP", "mentionSuggestionChar": "{{"},
                    }
                ],
            }
        ],
    }
    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Source {suffix}", "content_json": body},
    ).json()

    links = _links(api_client, headers, project_id, source_type="REQ", source_id=source["id"])
    assert links == []


def test_a_spec_can_tag_a_requirement(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Spec tags req {suffix}")["id"]

    requirement = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Requirement {suffix}"},
    ).json()

    spec = api_client.post(
        f"/api/projects/{project_id}/documents",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Spec {suffix}",
            "doc_type": "SPEC",
            "content_json": _body_tagging("REQ", requirement["id"]),
        },
    )
    assert spec.status_code in (200, 201), spec.text

    links = _links(api_client, headers, project_id, source_type="SPEC", source_id=spec.json()["id"])
    assert [(l["target_type"], l["target_id"], l["role"]) for l in links] == [
        ("REQ", requirement["id"], "references")
    ]


def test_a_requirement_can_tag_another_requirement(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Req tags req {suffix}")["id"]

    target = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Target {suffix}"},
    ).json()
    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Source {suffix}",
            "content_json": _body_tagging("REQ", target["id"]),
        },
    )
    assert source.status_code in (200, 201), source.text

    links = _links(
        api_client, headers, project_id, source_type="REQ", source_id=source.json()["id"]
    )
    assert [(l["target_type"], l["target_id"], l["role"]) for l in links] == [
        ("REQ", target["id"], "references")
    ]


def test_a_requirement_can_tag_a_design(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Req tags des {suffix}")["id"]

    design = api_client.post(
        "/api/designs",
        headers=headers,
        json={"project_id": project_id, "title": f"Design {suffix}"},
    )
    assert design.status_code in (200, 201), design.text

    source = api_client.post(
        "/api/requirements",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Source {suffix}",
            "content_json": _body_tagging("DES", design.json()["id"]),
        },
    ).json()

    links = _links(api_client, headers, project_id, source_type="REQ", source_id=source["id"])
    assert [(l["target_type"], l["target_id"], l["role"]) for l in links] == [
        ("DES", design.json()["id"], "references")
    ]


def test_a_test_case_body_hosts_no_tags(api_client: TestClient):
    headers = _admin_headers(api_client)
    suffix = unique_suffix()
    project_id = create_project(api_client, headers, f"Case {suffix}")["id"]

    requirement = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project_id, "title": f"Requirement {suffix}"},
    ).json()

    case = api_client.post(
        "/api/test-cases",
        headers=headers,
        json={
            "project_id": project_id,
            "title": f"Case {suffix}",
            "content_json": _body_tagging("REQ", requirement["id"]),
        },
    )
    assert case.status_code in (200, 201), case.text

    links = _links(api_client, headers, project_id, source_type="TC", source_id=case.json()["id"])
    assert links == []
