"""The tag base, an artefact's tags, and the tags a policy ticks per document type deciding
what a user sees."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from fastapi.testclient import TestClient

from tests.api.test_groups_http import (
    _admin_headers,
    _create_group,
    _create_user,
    _headers_for,
)
from tests.conftest import create_project, unique_name


def _tag(api_client, admin):
    created = api_client.post("/api/tags", headers=admin, json={"name": unique_name("tag")})
    assert created.status_code == 201, created.text
    return created.json()


def _requirement(api_client, admin, project, origin="Customer"):
    made = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "req_origin": origin},
    )
    assert made.status_code == 201, made.text
    return made.json()


def _tag_it(api_client, headers, kind, artefact_id, tag_ids):
    return api_client.put(
        f"/api/artefacts/{kind}/{artefact_id}/tags", headers=headers, json={"tag_ids": tag_ids}
    )


def _member(api_client, admin, project, role, rules, *more_rules):
    policy_ids = []
    for each in (rules, *more_rules):
        policy = api_client.post(
            "/api/policies",
            headers=admin,
            json={"name": unique_name("Policy"), "rules": each},
        )
        assert policy.status_code == 201, policy.text
        policy_ids.append(policy.json()["id"])
    group = _create_group(api_client, admin)
    assigned = api_client.patch(
        f"/api/groups/{group['id']}", headers=admin, json={"policy_ids": policy_ids}
    )
    assert assigned.status_code == 200, assigned.text
    granted = api_client.post(
        f"/api/groups/{group['id']}/grants",
        headers=admin,
        json={"project_id": project},
    )
    assert granted.status_code == 201, granted.text
    user = _create_user(api_client, admin, role=role)
    added = api_client.post(
        f"/api/groups/{group['id']}/members", headers=admin, json={"user_id": user["id"]}
    )
    assert added.status_code == 201, added.text
    return _headers_for(api_client, user["email"])


def test_the_tag_base_is_managed_by_administrators(api_client: TestClient):
    admin = _admin_headers(api_client)
    tag = _tag(api_client, admin)
    renamed = api_client.patch(
        f"/api/tags/{tag['id']}", headers=admin, json={"name": tag["name"] + "-x"}
    )
    assert renamed.status_code == 200 and renamed.json()["name"] == tag["name"] + "-x"
    clash = api_client.post("/api/tags", headers=admin, json={"name": tag["name"] + "-x"})
    assert clash.status_code == 409
    user = _create_user(api_client, admin, role="maintainer")
    headers = _headers_for(api_client, user["email"])
    assert api_client.post("/api/tags", headers=headers, json={"name": "x"}).status_code == 403
    unknown = api_client.post(
        "/api/policies",
        headers=admin,
        json={"name": unique_name("P"), "rules": {"REQ": {"read": True, "tags": [999999]}}},
    )
    assert unknown.status_code == 400


def test_an_external_user_sees_only_artefacts_with_their_tags(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Tagged")["id"]
    mine, other = _tag(api_client, admin), _tag(api_client, admin)
    shown, hidden, untagged = (_requirement(api_client, admin, project) for _ in range(3))
    assert _tag_it(api_client, admin, "requirement", shown["id"], [mine["id"]]).status_code == 200
    assert _tag_it(api_client, admin, "requirement", hidden["id"], [other["id"]]).status_code == 200
    headers = _member(
        api_client, admin, project, "external", {"REQ": {"read": True, "tags": [mine["id"]]}}
    )

    listed = api_client.get(f"/api/requirements?project_id={project}", headers=headers).json()
    assert [r["id"] for r in listed["items"]] == [shown["id"]]
    for row in (hidden, untagged):
        assert api_client.get(f"/api/requirements/{row['id']}", headers=headers).status_code == 404
    seen = api_client.get(f"/api/artefacts/requirement/{shown['id']}/tags", headers=headers)
    assert [t["id"] for t in seen.json()] == [mine["id"]]
    offered = api_client.get(f"/api/tags?project_id={project}", headers=headers).json()
    assert [t["id"] for t in offered] == [mine["id"]]
    refused = _tag_it(api_client, headers, "requirement", shown["id"], [mine["id"]])
    assert refused.status_code == 403


def test_an_editor_changes_only_the_tags_their_policies_tick(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Scoped")["id"]
    mine, also_mine, other = (_tag(api_client, admin) for _ in range(3))
    row = _requirement(api_client, admin, project, origin="Internal")
    assert (
        _tag_it(api_client, admin, "requirement", row["id"], [mine["id"], other["id"]]).status_code
        == 200
    )
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "write": True, "tags": [mine["id"], also_mine["id"]]}},
    )

    added = _tag_it(api_client, headers, "requirement", row["id"], [mine["id"], also_mine["id"]])
    assert added.status_code == 200, added.text
    assert sorted(t["id"] for t in added.json()) == sorted([mine["id"], also_mine["id"]])
    foreign = _tag(api_client, admin)
    outside = _tag_it(api_client, headers, "requirement", row["id"], [mine["id"], foreign["id"]])
    assert outside.status_code == 403
    assert outside.json()["detail"] == "Only tags your policies tick can be added or removed."
    emptied = _tag_it(api_client, headers, "requirement", row["id"], [])
    assert emptied.status_code == 403
    assert emptied.json()["detail"] == "The artefact must stay inside your policies."
    narrowed = _tag_it(api_client, headers, "requirement", row["id"], [also_mine["id"]])
    assert [t["id"] for t in narrowed.json()] == [also_mine["id"]]
    full = api_client.get(f"/api/artefacts/requirement/{row['id']}/tags", headers=admin).json()
    assert sorted(t["id"] for t in full) == sorted([also_mine["id"], other["id"]])


def test_a_policy_ticking_customer_shows_customer_artefacts_only(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Customer only")["id"]
    shown = _requirement(api_client, admin, project, origin="Customer")
    hidden = _requirement(api_client, admin, project, origin="Internal")
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "visibility": ["customer"]}},
    )
    listed = api_client.get(f"/api/requirements?project_id={project}", headers=headers).json()
    assert [r["id"] for r in listed["items"]] == [shown["id"]]
    assert api_client.get(f"/api/requirements/{hidden['id']}", headers=headers).status_code == 404


def test_a_scoped_user_creates_with_one_of_their_tags(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Created")["id"]
    first, second, foreign = (_tag(api_client, admin) for _ in range(3))
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "write": True, "tags": [first["id"], second["id"]]}},
    )

    def create(tag_ids):
        return api_client.post(
            "/api/requirements",
            headers=headers,
            json={"project_id": project, "title": unique_name("req"), "tag_ids": tag_ids},
        )

    missing = create([])
    assert missing.status_code == 403
    assert missing.json()["detail"] == "No create policy covers this artefact."
    outside = create([first["id"], foreign["id"]])
    assert outside.status_code == 403
    assert outside.json()["detail"] == "Only tags your policies tick can be given."
    made = create([second["id"]])
    assert made.status_code == 201, made.text
    listed = api_client.get(f"/api/requirements?project_id={project}", headers=headers).json()
    assert [r["id"] for r in listed["items"]] == [made.json()["id"]]
    carried = api_client.get(f"/api/artefacts/requirement/{made.json()['id']}/tags", headers=admin)
    assert [t["id"] for t in carried.json()] == [second["id"]]


def test_an_unscoped_user_may_give_any_tag_or_none(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Free")["id"]
    tag = _tag(api_client, admin)
    for tag_ids, expected in (([], []), ([tag["id"]], [tag["id"]])):
        made = api_client.post(
            "/api/requirements",
            headers=admin,
            json={"project_id": project, "title": unique_name("req"), "tag_ids": tag_ids},
        )
        assert made.status_code == 201, made.text
        carried = api_client.get(
            f"/api/artefacts/requirement/{made.json()['id']}/tags", headers=admin
        ).json()
        assert [t["id"] for t in carried] == expected
    unknown = api_client.post(
        "/api/requirements",
        headers=admin,
        json={"project_id": project, "title": unique_name("req"), "tag_ids": [999999]},
    )
    assert unknown.status_code == 400


def test_the_create_form_learns_the_users_tag_scope(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Scope")["id"]
    mine, other = _tag(api_client, admin), _tag(api_client, admin)
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "write": True, "tags": [mine["id"]]}},
    )
    limited = api_client.get(f"/api/tags/scope?project_id={project}", headers=headers).json()
    assert limited["limited"] is True
    assert [t["id"] for t in limited["tags"]] == [mine["id"]]
    free = api_client.get(f"/api/tags/scope?project_id={project}", headers=admin).json()
    assert free["limited"] is False
    assert {mine["id"], other["id"]} <= {t["id"] for t in free["tags"]}


def test_an_import_by_a_scoped_user_needs_one_of_their_tags(api_client: TestClient, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "REQIF_IMPORTS_PER_15_MINUTES", 100)
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Imported")["id"]
    first, second = _tag(api_client, admin), _tag(api_client, admin)
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {
            "TC": {"read": True, "write": True, "tags": [first["id"], second["id"]]},
            "TS": {"read": True, "write": True, "tags": [first["id"], second["id"]]},
        },
    )
    export = (
        "<suite><sections><section><name>Boot</name><cases><case><id>C1</id>"
        "<title>Cold boot</title></case></cases></section></sections></suite>"
    ).encode()

    def run(params):
        return api_client.post(
            f"/api/projects/{project}/import/testrail",
            headers=headers,
            params=params,
            files={"file": ("t.xml", export, "application/xml")},
        )

    refused = run({"format": "xml"})
    assert refused.status_code == 201, refused.text
    assert refused.json()["created"] == 0
    assert refused.json()["errors"] == ["case C1: not permitted"]
    made = run({"format": "xml", "tag_ids": [second["id"]]})
    assert made.status_code == 201, made.text
    listed = api_client.get(f"/api/test-cases?project_id={project}", headers=headers).json()
    assert len(listed["items"]) == 1
    case = listed["items"][0]["id"]
    carried = api_client.get(f"/api/artefacts/test-case/{case}/tags", headers=admin).json()
    assert [t["id"] for t in carried] == [second["id"]]


def test_a_visibility_change_needs_a_write_policy_ticking_the_new_visibility(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Retag")["id"]
    row = _requirement(api_client, admin, project, origin="Internal")
    narrow = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "write": True, "visibility": ["internal"]}},
        {"REQ": {"read": True, "visibility": ["customer"]}},
    )
    refused = api_client.patch(
        f"/api/requirements/{row['id']}", headers=narrow, json={"req_origin": "Customer"}
    )
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "No edit policy covers this visibility."
    wide = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "write": True, "visibility": ["internal", "customer"]}},
    )
    moved = api_client.patch(
        f"/api/requirements/{row['id']}", headers=wide, json={"req_origin": "Customer"}
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["visibility"] == "customer"


def test_a_tag_only_a_read_policy_ticks_cannot_be_added(api_client: TestClient):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Read tag")["id"]
    seen = _tag(api_client, admin)
    row = _requirement(api_client, admin, project, origin="Internal")
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "write": True, "visibility": ["internal"]}},
        {"REQ": {"read": True, "tags": [seen["id"]]}},
    )
    refused = _tag_it(api_client, headers, "requirement", row["id"], [seen["id"]])
    assert refused.status_code == 403, refused.text
    assert refused.json()["detail"] == "Only tags your policies tick can be added or removed."


def test_an_import_does_not_overwrite_a_test_case_the_importer_cannot_edit(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Import edit")["id"]
    internal = api_client.post(
        "/api/test-cases",
        headers=admin,
        json={"project_id": project, "title": "Kept", "visibility": "internal"},
    ).json()
    headers = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"TC": {"read": True, "write": True, "visibility": ["customer"]}},
        {"TC": {"read": True, "visibility": ["internal"]}},
    )
    csv = f"tc_id,title,visibility\n{internal['tc_id']},Overwritten,customer\n".encode()
    result = api_client.post(
        f"/api/projects/{project}/import/test-cases",
        headers=headers,
        params={"format": "csv"},
        files={"file": ("cases.csv", csv, "text/csv")},
    )
    assert result.status_code == 201, result.text
    assert result.json()["updated"] == 0
    stored = api_client.get(f"/api/test-cases/{internal['id']}", headers=admin).json()
    assert (stored["title"], stored["visibility"]) == ("Kept", "internal")


def test_a_baseline_shows_a_section_only_to_who_sees_every_row_of_its_type(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "Snapshot")["id"]
    _requirement(api_client, admin, project, origin="Internal")
    baseline = api_client.post(
        "/api/baselines", headers=admin, json={"project_id": project, "name": "B1"}
    ).json()
    tag = _tag(api_client, admin)
    limited = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "tags": [tag["id"]]}, "baseline": {"read": True}},
    )
    split = _member(
        api_client,
        admin,
        project,
        "maintainer",
        {"REQ": {"read": True, "visibility": ["internal"]}, "baseline": {"read": True}},
        {"REQ": {"read": True, "visibility": ["customer"]}},
    )
    for headers, shown in ((limited, False), (split, True)):
        snapshot = api_client.get(f"/api/baselines/{baseline['id']}", headers=headers).json()[
            "snapshot"
        ]
        assert ("requirements" in snapshot) is shown


def test_an_external_user_neither_deletes_nor_approves_even_with_write_and_delete(
    api_client: TestClient,
):
    admin = _admin_headers(api_client)
    project = create_project(api_client, admin, "External delete")["id"]
    headers = _member(
        api_client,
        admin,
        project,
        "external",
        {
            "REQ": {
                "read": True,
                "write": True,
                "approve": True,
                "delete": True,
                "visibility": ["customer"],
            }
        },
    )
    effective = api_client.get(f"/api/projects/{project}/permissions", headers=headers).json()
    assert not {"approve", "delete"} & set(effective["REQ"])
    own = api_client.post(
        "/api/requirements",
        headers=headers,
        json={"project_id": project, "title": unique_name("req")},
    )
    assert own.status_code == 201, own.text
    deleted = api_client.delete(f"/api/requirements/{own.json()['id']}", headers=headers)
    assert deleted.status_code == 403, deleted.text
