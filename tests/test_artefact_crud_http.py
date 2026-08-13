"""CRUD across the controlled artefacts: defects, changes, risks, baselines.

Each type has its own router with the same shape - list, create, read, patch,
delete - and the same guards around project access, terminal statuses and
external tracker references. These drive the real routes so those guards are
exercised rather than assumed.
"""

from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest
from fastapi.testclient import TestClient

from tests.conftest import create_project, unique_email


@pytest.fixture
def auth_headers(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def project(api_client: TestClient, auth_headers):
    return create_project(api_client, auth_headers, "Artefact CRUD")


class TestDefects:
    def test_creates_and_numbers_a_defect(self, api_client, auth_headers, project):
        response = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Screen flickers", "severity": "High"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["defect_id"].startswith(f"{project['prefix']}-DEF-")
        assert body["severity"] == "High"

    def test_identifiers_increment(self, api_client, auth_headers, project):
        first = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "First"},
        ).json()
        second = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Second"},
        ).json()
        assert first["defect_id"] != second["defect_id"]

    def test_creating_in_an_unknown_project_is_404(self, api_client, auth_headers):
        response = api_client.post(
            "/api/defects", headers=auth_headers, json={"project_id": 999999, "title": "Orphan"}
        )
        assert response.status_code == 404

    def test_lists_and_filters_by_severity(self, api_client, auth_headers, project):
        api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Critical one", "severity": "Critical"},
        )
        api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Low one", "severity": "Low"},
        )

        listed = api_client.get(
            f"/api/defects?project_id={project['id']}&severity=Critical", headers=auth_headers
        )
        assert listed.status_code == 200, listed.text
        assert {d["severity"] for d in listed.json()["items"]} == {"Critical"}

    def test_lists_and_filters_by_status(self, api_client, auth_headers, project):
        api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Open one"},
        )
        listed = api_client.get(
            f"/api/defects?project_id={project['id']}&status=Open", headers=auth_headers
        )
        assert listed.status_code == 200
        assert all(d["status"] == "Open" for d in listed.json()["items"])

    def test_fetches_one_defect(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Fetchable"},
        ).json()
        fetched = api_client.get(f"/api/defects/{created['id']}", headers=auth_headers)
        assert fetched.status_code == 200
        assert fetched.json()["title"] == "Fetchable"

    def test_unknown_defect_is_404(self, api_client, auth_headers):
        assert api_client.get("/api/defects/999999", headers=auth_headers).status_code == 404

    def test_patches_a_defect(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Before"},
        ).json()
        patched = api_client.patch(
            f"/api/defects/{created['id']}",
            headers=auth_headers,
            json={"title": "After", "severity": "Critical"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["title"] == "After"
        assert patched.json()["severity"] == "Critical"

    def test_closing_a_defect_stamps_closed_at(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "To close"},
        ).json()
        assert created["closed_at"] is None

        closed = api_client.patch(
            f"/api/defects/{created['id']}", headers=auth_headers, json={"status": "Closed"}
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["closed_at"] is not None

    def test_reopening_clears_closed_at(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "To reopen"},
        ).json()
        api_client.patch(
            f"/api/defects/{created['id']}", headers=auth_headers, json={"status": "Closed"}
        )
        reopened = api_client.patch(
            f"/api/defects/{created['id']}", headers=auth_headers, json={"status": "Open"}
        )
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()["closed_at"] is None

    def test_rejects_an_unsupported_tracker(self, api_client, auth_headers, project):
        response = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={
                "project_id": project["id"],
                "title": "Bad tracker",
                "external_tracker": "bugzilla",
            },
        )
        assert response.status_code == 422
        assert "unsupported tracker" in response.json()["detail"].lower()

    def test_rejects_a_url_that_contradicts_the_tracker(self, api_client, auth_headers, project):
        """The reference must be internally consistent, not merely present."""
        response = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={
                "project_id": project["id"],
                "title": "Mismatched",
                "external_tracker": "gitlab",
                "external_issue_url": "https://github.com/acme/widget/issues/7",
            },
        )
        assert response.status_code == 422

    def test_rejects_an_unparseable_issue_url(self, api_client, auth_headers, project):
        response = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={
                "project_id": project["id"],
                "title": "Bad url",
                "external_issue_url": "not-a-url",
            },
        )
        assert response.status_code == 422

    def test_patching_an_unknown_defect_is_404(self, api_client, auth_headers):
        response = api_client.patch(
            "/api/defects/999999", headers=auth_headers, json={"title": "x"}
        )
        assert response.status_code == 404

    def test_deletes_a_defect(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Deletable"},
        ).json()
        assert (
            api_client.delete(f"/api/defects/{created['id']}", headers=auth_headers).status_code
            == 204
        )
        assert (
            api_client.get(f"/api/defects/{created['id']}", headers=auth_headers).status_code == 404
        )

    def test_deleting_an_unknown_defect_is_404(self, api_client, auth_headers):
        assert api_client.delete("/api/defects/999999", headers=auth_headers).status_code == 404

    def test_refresh_external_requires_a_reference(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/defects",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "No tracker"},
        ).json()
        response = api_client.post(
            f"/api/defects/{created['id']}/refresh-external", headers=auth_headers, json={}
        )
        assert response.status_code == 422
        assert "external issue" in response.json()["detail"].lower()


class TestChangeRequests:
    def test_creates_and_numbers_a_change(self, api_client, auth_headers, project):
        response = api_client.post(
            "/api/changes",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Move to CAN FD"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["change_id"].startswith(f"{project['prefix']}-CHG-")

    def test_creating_in_an_unknown_project_is_404(self, api_client, auth_headers):
        response = api_client.post(
            "/api/changes", headers=auth_headers, json={"project_id": 999999, "title": "Orphan"}
        )
        assert response.status_code == 404

    def test_lists_changes_for_a_project(self, api_client, auth_headers, project):
        api_client.post(
            "/api/changes",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Listed"},
        )
        listed = api_client.get(f"/api/changes?project_id={project['id']}", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] >= 1

    def test_reads_patches_and_deletes(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/changes",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Round trip"},
        ).json()

        assert (
            api_client.get(f"/api/changes/{created['id']}", headers=auth_headers).status_code == 200
        )

        patched = api_client.patch(
            f"/api/changes/{created['id']}",
            headers=auth_headers,
            json={"status": "Approved", "priority": "High"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["status"] == "Approved"

        assert (
            api_client.delete(f"/api/changes/{created['id']}", headers=auth_headers).status_code
            == 204
        )
        assert (
            api_client.get(f"/api/changes/{created['id']}", headers=auth_headers).status_code == 404
        )

    def test_unknown_change_is_404(self, api_client, auth_headers):
        assert api_client.get("/api/changes/999999", headers=auth_headers).status_code == 404
        assert (
            api_client.patch(
                "/api/changes/999999", headers=auth_headers, json={"title": "x"}
            ).status_code
            == 404
        )
        assert api_client.delete("/api/changes/999999", headers=auth_headers).status_code == 404


class TestRisks:
    def test_creates_and_numbers_a_risk(self, api_client, auth_headers, project):
        response = api_client.post(
            "/api/risks",
            headers=auth_headers,
            json={
                "project_id": project["id"],
                "title": "Thermal runaway",
                "severity": "Critical",
                "probability": "Low",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["risk_id"].startswith(f"{project['prefix']}-RSK-")
        assert body["severity"] == "Critical"

    def test_creating_in_an_unknown_project_is_404(self, api_client, auth_headers):
        response = api_client.post(
            "/api/risks", headers=auth_headers, json={"project_id": 999999, "title": "Orphan"}
        )
        assert response.status_code == 404

    def test_lists_risks_for_a_project(self, api_client, auth_headers, project):
        api_client.post(
            "/api/risks",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Listed"},
        )
        listed = api_client.get(f"/api/risks?project_id={project['id']}", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] >= 1

    def test_reads_patches_and_deletes(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/risks",
            headers=auth_headers,
            json={"project_id": project["id"], "title": "Round trip"},
        ).json()

        assert (
            api_client.get(f"/api/risks/{created['id']}", headers=auth_headers).status_code == 200
        )

        patched = api_client.patch(
            f"/api/risks/{created['id']}",
            headers=auth_headers,
            json={"status": "Mitigated", "mitigation": "Added a fuse"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["mitigation"] == "Added a fuse"

        assert (
            api_client.delete(f"/api/risks/{created['id']}", headers=auth_headers).status_code
            == 204
        )

    def test_unknown_risk_is_404(self, api_client, auth_headers):
        assert api_client.get("/api/risks/999999", headers=auth_headers).status_code == 404
        assert api_client.delete("/api/risks/999999", headers=auth_headers).status_code == 404


class TestBaselines:
    def test_creates_a_baseline(self, api_client, auth_headers, project):
        response = api_client.post(
            "/api/baselines",
            headers=auth_headers,
            json={"project_id": project["id"], "name": "Release 1.0", "baseline_type": "Release"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["name"] == "Release 1.0"

    def test_lists_baselines(self, api_client, auth_headers, project):
        api_client.post(
            "/api/baselines",
            headers=auth_headers,
            json={"project_id": project["id"], "name": "Listed"},
        )
        listed = api_client.get("/api/baselines", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert any(b["name"] == "Listed" for b in listed.json())

    def test_filters_baselines_by_project(self, api_client, auth_headers, project):
        api_client.post(
            "/api/baselines",
            headers=auth_headers,
            json={"project_id": project["id"], "name": "Scoped"},
        )
        listed = api_client.get(f"/api/baselines?project_id={project['id']}", headers=auth_headers)
        assert listed.status_code == 200
        assert all(b["project_id"] == project["id"] for b in listed.json())

    def test_reads_patches_and_deletes(self, api_client, auth_headers, project):
        created = api_client.post(
            "/api/baselines",
            headers=auth_headers,
            json={"project_id": project["id"], "name": "Round trip"},
        ).json()

        assert (
            api_client.get(f"/api/baselines/{created['id']}", headers=auth_headers).status_code
            == 200
        )

        patched = api_client.patch(
            f"/api/baselines/{created['id']}", headers=auth_headers, json={"name": "Renamed"}
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["name"] == "Renamed"

        assert (
            api_client.delete(f"/api/baselines/{created['id']}", headers=auth_headers).status_code
            == 204
        )

    def test_unknown_baseline_is_404(self, api_client, auth_headers):
        assert api_client.get("/api/baselines/999999", headers=auth_headers).status_code == 404
        assert api_client.delete("/api/baselines/999999", headers=auth_headers).status_code == 404


class TestProjectMembers:
    @pytest.fixture
    def member(self, api_client, auth_headers):
        email = unique_email("member")
        created = api_client.post(
            "/api/users",
            headers=auth_headers,
            json={
                "email": email,
                "full_name": "Member",
                "password": "a-long-enough-password",
                "role": "maintainer",
            },
        )
        assert created.status_code in (200, 201), created.text
        return created.json()

    def test_adds_and_lists_a_member(self, api_client, auth_headers, project, member):
        added = api_client.post(
            f"/api/projects/{project['id']}/members",
            headers=auth_headers,
            json={"user_id": member["id"], "role": "maintainer"},
        )
        assert added.status_code == 201, added.text

        listed = api_client.get(f"/api/projects/{project['id']}/members", headers=auth_headers)
        assert listed.status_code == 200, listed.text
        assert any(m["user_id"] == member["id"] for m in listed.json())

    def test_reads_one_membership(self, api_client, auth_headers, project, member):
        added = api_client.post(
            f"/api/projects/{project['id']}/members",
            headers=auth_headers,
            json={"user_id": member["id"], "role": "maintainer"},
        ).json()
        fetched = api_client.get(
            f"/api/projects/{project['id']}/members/{added['id']}", headers=auth_headers
        )
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["user_id"] == member["id"]

    def test_changes_a_member_role(self, api_client, auth_headers, project, member):
        added = api_client.post(
            f"/api/projects/{project['id']}/members",
            headers=auth_headers,
            json={"user_id": member["id"], "role": "maintainer"},
        ).json()
        patched = api_client.patch(
            f"/api/projects/{project['id']}/members/{added['id']}",
            headers=auth_headers,
            json={"role": "external", "doc_types": ["REQ"]},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["role"] == "external"

    def test_rejects_a_membership_role_outside_the_project_roles(
        self, api_client, auth_headers, project, member
    ):
        """Project membership grants maintainer or external; viewer is global."""
        added = api_client.post(
            f"/api/projects/{project['id']}/members",
            headers=auth_headers,
            json={"user_id": member["id"], "role": "maintainer"},
        ).json()
        response = api_client.patch(
            f"/api/projects/{project['id']}/members/{added['id']}",
            headers=auth_headers,
            json={"role": "viewer"},
        )
        assert response.status_code == 422

    def test_removes_a_member(self, api_client, auth_headers, project, member):
        added = api_client.post(
            f"/api/projects/{project['id']}/members",
            headers=auth_headers,
            json={"user_id": member["id"], "role": "maintainer"},
        ).json()
        removed = api_client.delete(
            f"/api/projects/{project['id']}/members/{added['id']}", headers=auth_headers
        )
        assert removed.status_code == 204, removed.text

        listed = api_client.get(f"/api/projects/{project['id']}/members", headers=auth_headers)
        assert not any(m["id"] == added["id"] for m in listed.json())

    def test_adding_an_unknown_user_is_refused(self, api_client, auth_headers, project):
        response = api_client.post(
            f"/api/projects/{project['id']}/members",
            headers=auth_headers,
            json={"user_id": 999999, "role": "maintainer"},
        )
        assert response.status_code in (400, 404, 422)

    def test_unknown_membership_is_404(self, api_client, auth_headers, project):
        assert (
            api_client.get(
                f"/api/projects/{project['id']}/members/999999", headers=auth_headers
            ).status_code
            == 404
        )
        assert (
            api_client.delete(
                f"/api/projects/{project['id']}/members/999999", headers=auth_headers
            ).status_code
            == 404
        )


class TestAuthenticationIsRequired:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/defects?project_id=1"),
            ("POST", "/api/defects"),
            ("GET", "/api/defects/1"),
            ("PATCH", "/api/defects/1"),
            ("DELETE", "/api/defects/1"),
            ("GET", "/api/changes?project_id=1"),
            ("POST", "/api/changes"),
            ("GET", "/api/risks?project_id=1"),
            ("POST", "/api/risks"),
            ("GET", "/api/baselines"),
            ("POST", "/api/baselines"),
            ("GET", "/api/projects/1/members"),
            ("POST", "/api/projects/1/members"),
        ],
    )
    def test_every_route_refuses_an_anonymous_caller(self, api_client, method, path):
        response = api_client.request(method, path, json={})
        assert response.status_code == 401, f"{method} {path} was {response.status_code}"
