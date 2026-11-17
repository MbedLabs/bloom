"""
* @file     ${tests/api/artefact_crud.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests creating, reading, changing and deleting defects, changes, risks, baselines and members.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the artefact CRUD routes.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactCrudBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_defect_is_created_and_numbered(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "Screen flickers", "severity": "High"},
        )
        self.assertEqual(
            (
                answer.status,
                answer.body["defect_id"].startswith(f"{self.project['prefix']}-DEF-"),
                answer.body["severity"],
            ),
            (values.STATUS_CREATED, True, "High"),
            msg=values.MSG_CRUD_DEFECT_CREATED,
            abort_on_fail=False,
        )

    def bud_defect_ids_increase(self):
        values = self.parameters
        first, second = (
            self.bloom.bloom_api_call(
                "POST",
                "/api/defects",
                self.admin,
                json={"project_id": self.project["id"], "title": "First"},
            ).body,
            self.bloom.bloom_api_call(
                "POST",
                "/api/defects",
                self.admin,
                json={"project_id": self.project["id"], "title": "Second"},
            ).body,
        )
        self.assertNotEqual(
            first["defect_id"],
            second["defect_id"],
            msg=values.MSG_CRUD_DEFECT_IDS,
            abort_on_fail=False,
        )

    def bud_a_defect_in_an_unknown_project_is_a_404(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST", "/api/defects", self.admin, json={"project_id": 999999, "title": "Orphan"}
        )
        self.assertEqual(
            answer.status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_CRUD_UNKNOWN_PROJECT.format(kind="defect"),
            abort_on_fail=False,
        )

    def bud_defects_are_filtered_by_severity_and_status(self):
        values = self.parameters
        self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={
                "project_id": self.project["id"],
                "title": "Critical one",
                "severity": "Critical",
            },
        )
        self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "Low one", "severity": "Low"},
        )
        critical = self.bloom.bloom_api_call(
            "GET",
            "/api/defects",
            self.admin,
            params={"project_id": self.project["id"], "severity": "Critical"},
        )
        self.assertEqual(
            (critical.status, {d["severity"] for d in critical.body["items"]}),
            (values.STATUS_OK, {"Critical"}),
            msg=values.MSG_CRUD_DEFECT_SEVERITY,
            abort_on_fail=False,
        )
        opened = self.bloom.bloom_api_call(
            "GET",
            "/api/defects",
            self.admin,
            params={"project_id": self.project["id"], "status": "Open"},
        )
        self.assertEqual(
            (opened.status, {d["status"] for d in opened.body["items"]}),
            (values.STATUS_OK, {"Open"}),
            msg=values.MSG_CRUD_DEFECT_STATUS,
            abort_on_fail=False,
        )

    def bud_a_defect_is_read_by_its_id(self):
        values = self.parameters
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "Fetchable"},
        ).body
        fetched = self.bloom.bloom_api_call("GET", f"/api/defects/{created['id']}", self.admin)
        self.assertEqual(
            (
                fetched.status,
                fetched.body["title"],
                self.bloom.bloom_api_call("GET", "/api/defects/999999", self.admin).status,
            ),
            (values.STATUS_OK, "Fetchable", values.STATUS_NOT_FOUND),
            msg=values.MSG_CRUD_DEFECT_READ,
            abort_on_fail=False,
        )

    def bud_a_defect_is_changed(self):
        values = self.parameters
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "Before"},
        ).body
        patched = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/defects/{created['id']}",
            self.admin,
            json={"title": "After", "severity": "Critical"},
        )
        self.assertEqual(
            (patched.status, patched.body["title"], patched.body["severity"]),
            (values.STATUS_OK, "After", "Critical"),
            msg=values.MSG_CRUD_DEFECT_PATCHED,
            abort_on_fail=False,
        )

    def bud_closing_and_reopening_a_defect_stamps_its_closing_time(self):
        values = self.parameters
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "To close"},
        ).body
        path = f"/api/defects/{created['id']}"
        closed = self.bloom.bloom_api_call("PATCH", path, self.admin, json={"status": "Closed"})
        reopened = self.bloom.bloom_api_call("PATCH", path, self.admin, json={"status": "Open"})
        self.assertEqual(
            (
                created["closed_at"],
                closed.status,
                closed.body["closed_at"] is not None,
                reopened.status,
                reopened.body["closed_at"],
            ),
            (None, values.STATUS_OK, True, values.STATUS_OK, None),
            msg=values.MSG_CRUD_DEFECT_CLOSED,
            abort_on_fail=False,
        )

    def bud_a_wrong_issue_reference_is_refused_422(self):
        values = self.parameters
        cases = (
            ("an unsupported tracker", {"external_tracker": "bugzilla"}, "unsupported tracker"),
            (
                "a link contradicting the tracker",
                {
                    "external_tracker": "gitlab",
                    "external_issue_url": "https://github.com/acme/widget/issues/7",
                },
                "",
            ),
            ("an unreadable issue link", {"external_issue_url": "not-a-url"}, ""),
        )
        for what, fields, phrase in cases:
            answer = self.bloom.bloom_api_call(
                "POST",
                "/api/defects",
                self.admin,
                json={"project_id": self.project["id"], "title": what, **fields},
            )
            self.assertEqual(
                (answer.status, phrase in str(answer.body.get("detail", "")).lower()),
                (values.STATUS_UNPROCESSABLE, True),
                msg=values.MSG_CRUD_DEFECT_TRACKER.format(what=what),
                abort_on_fail=False,
            )

    def bud_an_unknown_defect_is_a_404(self):
        values = self.parameters
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "PATCH", "/api/defects/999999", self.admin, json={"title": "x"}
                ).status,
                self.bloom.bloom_api_call("DELETE", "/api/defects/999999", self.admin).status,
            ),
            (values.STATUS_NOT_FOUND,) * 2,
            msg=values.MSG_CRUD_UNKNOWN.format(kind="defect"),
            abort_on_fail=False,
        )

    def bud_a_deleted_defect_is_gone(self):
        values = self.parameters
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "Deletable"},
        ).body
        path = f"/api/defects/{created['id']}"
        self.assertEqual(
            (
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
                self.bloom.bloom_api_call("GET", path, self.admin).status,
            ),
            (values.STATUS_NO_CONTENT, values.STATUS_NOT_FOUND),
            msg=values.MSG_CRUD_DEFECT_DELETED,
            abort_on_fail=False,
        )

    def bud_refreshing_needs_an_issue_link_422(self):
        values = self.parameters
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": self.project["id"], "title": "No tracker"},
        ).body
        answer = self.bloom.bloom_api_call(
            "POST", f"/api/defects/{created['id']}/refresh-external", self.admin, json={}
        )
        self.assertEqual(
            (answer.status, "external issue" in answer.body["detail"].lower()),
            (values.STATUS_UNPROCESSABLE, True),
            msg=values.MSG_CRUD_DEFECT_REFRESH,
            abort_on_fail=False,
        )

    def bud_a_change_request_is_created_and_numbered(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST",
            "/api/changes",
            self.admin,
            json={"project_id": self.project["id"], "title": "Move to CAN FD"},
        )
        self.assertEqual(
            (answer.status, answer.body["change_id"].startswith(f"{self.project['prefix']}-CHG-")),
            (values.STATUS_CREATED, True),
            msg=values.MSG_CRUD_CHANGE_CREATED,
            abort_on_fail=False,
        )

    def bud_a_change_in_an_unknown_project_is_a_404(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST", "/api/changes", self.admin, json={"project_id": 999999, "title": "Orphan"}
        )
        self.assertEqual(
            answer.status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_CRUD_UNKNOWN_PROJECT.format(kind="change request"),
            abort_on_fail=False,
        )

    def bud_change_requests_go_through_their_round_trip(self):
        values = self.parameters
        self.bloom.bloom_api_call(
            "POST",
            "/api/changes",
            self.admin,
            json={"project_id": self.project["id"], "title": "Listed"},
        )
        listed = self.bloom.bloom_api_call(
            "GET", "/api/changes", self.admin, params={"project_id": self.project["id"]}
        )
        self.assertEqual(
            (listed.status, listed.body["total"] >= 1),
            (values.STATUS_OK, True),
            msg=values.MSG_CRUD_LISTED.format(kind="change request"),
            abort_on_fail=False,
        )
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/changes",
            self.admin,
            json={"project_id": self.project["id"], "title": "Round trip"},
        ).body
        path = f"/api/changes/{created['id']}"
        read = self.bloom.bloom_api_call("GET", path, self.admin).status
        patched = self.bloom.bloom_api_call("PATCH", path, self.admin, json={"priority": "High"})
        self.assertEqual(
            (
                read,
                patched.status,
                patched.body["status"],
                patched.body["priority"],
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
                self.bloom.bloom_api_call("GET", path, self.admin).status,
            ),
            (
                values.STATUS_OK,
                values.STATUS_OK,
                "Draft",
                "High",
                values.STATUS_NO_CONTENT,
                values.STATUS_NOT_FOUND,
            ),
            msg=values.MSG_CRUD_CHANGE_ROUND,
            abort_on_fail=False,
        )

    def bud_an_unknown_change_request_is_a_404(self):
        values = self.parameters
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/changes/999999", self.admin).status,
                self.bloom.bloom_api_call(
                    "PATCH", "/api/changes/999999", self.admin, json={"title": "x"}
                ).status,
                self.bloom.bloom_api_call("DELETE", "/api/changes/999999", self.admin).status,
            ),
            (values.STATUS_NOT_FOUND,) * 3,
            msg=values.MSG_CRUD_UNKNOWN.format(kind="change request"),
            abort_on_fail=False,
        )

    def bud_a_risk_is_created_and_numbered(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST",
            "/api/risks",
            self.admin,
            json={
                "project_id": self.project["id"],
                "title": "Thermal runaway",
                "severity": "Critical",
                "probability": "Low",
            },
        )
        self.assertEqual(
            (
                answer.status,
                answer.body["risk_id"].startswith(f"{self.project['prefix']}-RSK-"),
                answer.body["severity"],
            ),
            (values.STATUS_CREATED, True, "Critical"),
            msg=values.MSG_CRUD_RISK_CREATED,
            abort_on_fail=False,
        )

    def bud_a_risk_in_an_unknown_project_is_a_404(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST", "/api/risks", self.admin, json={"project_id": 999999, "title": "Orphan"}
        )
        self.assertEqual(
            answer.status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_CRUD_UNKNOWN_PROJECT.format(kind="risk"),
            abort_on_fail=False,
        )

    def bud_risks_go_through_their_round_trip(self):
        values = self.parameters
        self.bloom.bloom_api_call(
            "POST",
            "/api/risks",
            self.admin,
            json={"project_id": self.project["id"], "title": "Listed"},
        )
        listed = self.bloom.bloom_api_call(
            "GET", "/api/risks", self.admin, params={"project_id": self.project["id"]}
        )
        self.assertEqual(
            (listed.status, listed.body["total"] >= 1),
            (values.STATUS_OK, True),
            msg=values.MSG_CRUD_LISTED.format(kind="risk"),
            abort_on_fail=False,
        )
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/risks",
            self.admin,
            json={"project_id": self.project["id"], "title": "Round trip"},
        ).body
        path = f"/api/risks/{created['id']}"
        read = self.bloom.bloom_api_call("GET", path, self.admin).status
        patched = self.bloom.bloom_api_call(
            "PATCH", path, self.admin, json={"status": "Mitigated", "mitigation": "Added a fuse"}
        )
        self.assertEqual(
            (
                read,
                patched.status,
                patched.body["mitigation"],
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
            ),
            (values.STATUS_OK, values.STATUS_OK, "Added a fuse", values.STATUS_NO_CONTENT),
            msg=values.MSG_CRUD_RISK_ROUND,
            abort_on_fail=False,
        )

    def bud_an_unknown_risk_is_a_404(self):
        values = self.parameters
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/risks/999999", self.admin).status,
                self.bloom.bloom_api_call("DELETE", "/api/risks/999999", self.admin).status,
            ),
            (values.STATUS_NOT_FOUND,) * 2,
            msg=values.MSG_CRUD_UNKNOWN.format(kind="risk"),
            abort_on_fail=False,
        )

    def bud_a_baseline_is_created(self):
        values = self.parameters
        answer = self.bloom.bloom_api_call(
            "POST",
            "/api/baselines",
            self.admin,
            json={
                "project_id": self.project["id"],
                "name": "Release 1.0",
                "baseline_type": "Release",
            },
        )
        self.assertEqual(
            (answer.status, answer.body["name"]),
            (values.STATUS_CREATED, "Release 1.0"),
            msg=values.MSG_CRUD_BASELINE_CREATED,
            abort_on_fail=False,
        )

    def bud_baselines_are_listed_and_filtered_by_project(self):
        values = self.parameters
        self.bloom.bloom_api_call(
            "POST",
            "/api/baselines",
            self.admin,
            json={"project_id": self.project["id"], "name": "Listed"},
        )
        listed = self.bloom.bloom_api_call("GET", "/api/baselines", self.admin)
        scoped = self.bloom.bloom_api_call(
            "GET", "/api/baselines", self.admin, params={"project_id": self.project["id"]}
        )
        self.assertEqual(
            (
                listed.status,
                any(row["name"] == "Listed" for row in listed.body),
                scoped.status,
                {row["project_id"] for row in scoped.body},
            ),
            (values.STATUS_OK, True, values.STATUS_OK, {self.project["id"]}),
            msg=values.MSG_CRUD_BASELINE_LISTED,
            abort_on_fail=False,
        )

    def bud_baselines_go_through_their_round_trip(self):
        values = self.parameters
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/baselines",
            self.admin,
            json={"project_id": self.project["id"], "name": "Round trip"},
        ).body
        path = f"/api/baselines/{created['id']}"
        read = self.bloom.bloom_api_call("GET", path, self.admin).status
        patched = self.bloom.bloom_api_call("PATCH", path, self.admin, json={"name": "Renamed"})
        self.assertEqual(
            (
                read,
                patched.status,
                patched.body["name"],
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
            ),
            (values.STATUS_OK, values.STATUS_OK, "Renamed", values.STATUS_NO_CONTENT),
            msg=values.MSG_CRUD_BASELINE_ROUND,
            abort_on_fail=False,
        )

    def bud_an_unknown_baseline_is_a_404(self):
        values = self.parameters
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/baselines/999999", self.admin).status,
                self.bloom.bloom_api_call("DELETE", "/api/baselines/999999", self.admin).status,
            ),
            (values.STATUS_NOT_FOUND,) * 2,
            msg=values.MSG_CRUD_UNKNOWN.format(kind="baseline"),
            abort_on_fail=False,
        )

    def bud_a_member_is_added_listed_and_read(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "listed-member")
        policy = self.bloom.bloom_api_new_policy(self.admin, "listed-member policy", {"*": ["*"]})
        added = self.bloom.bloom_api_admit(
            self.admin, self.project["id"], user.id, policy_ids=[policy["id"]]
        )
        entry = f"/api/projects/{self.project['id']}/members/{added.body['id']}"
        listed = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{self.project['id']}/members", self.admin
        )
        fetched = self.bloom.bloom_api_call("GET", entry, self.admin)
        self.assertEqual(
            (
                added.status,
                any(m["user_id"] == user.id for m in listed.body),
                fetched.status,
                fetched.body["user_id"],
            ),
            (values.STATUS_CREATED, True, values.STATUS_OK, user.id),
            msg=values.MSG_CRUD_MEMBER_ADDED,
            abort_on_fail=False,
        )

    def bud_a_member_becomes_owner(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "owner-member")
        policy = self.bloom.bloom_api_new_policy(self.admin, "owner-member policy", {"*": ["*"]})
        added = self.bloom.bloom_api_admit(
            self.admin, self.project["id"], user.id, policy_ids=[policy["id"]]
        )
        entry = f"/api/projects/{self.project['id']}/members/{added.body['id']}"
        patched = self.bloom.bloom_api_call(
            "PATCH", entry, self.admin, json={"owner": True, "policy_ids": []}
        )
        self.assertEqual(
            (patched.status, patched.body["owner"], patched.body["policy_ids"]),
            (values.STATUS_OK, True, []),
            msg=values.MSG_CRUD_MEMBER_OWNER,
            abort_on_fail=False,
        )

    def bud_a_viewer_role_is_refused_422(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "viewer-member")
        policy = self.bloom.bloom_api_new_policy(self.admin, "viewer-member policy", {"*": ["*"]})
        added = self.bloom.bloom_api_admit(
            self.admin, self.project["id"], user.id, policy_ids=[policy["id"]]
        )
        entry = f"/api/projects/{self.project['id']}/members/{added.body['id']}"
        self.assertEqual(
            self.bloom.bloom_api_call("PATCH", entry, self.admin, json={"role": "viewer"}).status,
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_CRUD_MEMBER_ROLE,
            abort_on_fail=False,
        )

    def bud_a_removed_member_is_no_longer_listed(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "removed-member")
        policy = self.bloom.bloom_api_new_policy(self.admin, "removed-member policy", {"*": ["*"]})
        added = self.bloom.bloom_api_admit(
            self.admin, self.project["id"], user.id, policy_ids=[policy["id"]]
        )
        entry = f"/api/projects/{self.project['id']}/members/{added.body['id']}"
        removed = self.bloom.bloom_api_call("DELETE", entry, self.admin).status
        listed = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{self.project['id']}/members", self.admin
        ).body
        self.assertEqual(
            (removed, any(m["id"] == added.body["id"] for m in listed)),
            (values.STATUS_NO_CONTENT, False),
            msg=values.MSG_CRUD_MEMBER_REMOVED,
            abort_on_fail=False,
        )

    def bud_an_unknown_user_cannot_be_added(self):
        values = self.parameters
        policy = self.bloom.bloom_api_new_policy(self.admin, "Unknown user policy", {"*": ["*"]})
        answer = self.bloom.bloom_api_admit(
            self.admin, self.project["id"], 999999, policy_ids=[policy["id"]]
        )
        self.assertIn(
            answer.status,
            (values.STATUS_BAD_REQUEST, values.STATUS_NOT_FOUND, values.STATUS_UNPROCESSABLE),
            msg=values.MSG_CRUD_MEMBER_UNKNOWN_USER,
            abort_on_fail=False,
        )

    def bud_an_unknown_entry_is_a_404(self):
        values = self.parameters
        path = f"/api/projects/{self.project['id']}/members/999999"
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", path, self.admin).status,
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
            ),
            (values.STATUS_NOT_FOUND, values.STATUS_NOT_FOUND),
            msg=values.MSG_CRUD_MEMBER_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_every_route_refuses_an_anonymous_caller_401(self):
        values = self.parameters
        for method, path in values.CRUD_ANONYMOUS:
            answer = self.bloom.bloom_api_call(method, path, json={})
            self.assertEqual(
                answer.status,
                values.STATUS_UNAUTHORIZED,
                msg=values.MSG_CRUD_ANONYMOUS.format(method=method, path=path),
                abort_on_fail=False,
                method=method,
                endpoint=path,
            )
