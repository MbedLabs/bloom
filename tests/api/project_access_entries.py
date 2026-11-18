"""
* @file     ${tests/api/project_access_entries.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests direct project entries with policies or an owner grant.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the direct project entries.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectAccessEntriesBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_direct_policy_entry_controls_access_and_the_report(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PAE_PREFIXES[0])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "direct-entry")
        read = self.bloom.bloom_api_new_policy(self.admin, "Entry read", types=["REQ"])
        write = self.bloom.bloom_api_new_policy(
            self.admin, "Entry write", values.PAE_TC_WRITE, types=["TC"]
        )
        path = f"/api/projects/{project}/members"
        created = self.bloom.bloom_api_call(
            "POST",
            path,
            self.admin,
            json={"user_id": user.id, "policy_ids": [read["id"], write["id"]]},
        )
        entry = created.body
        self.print_variables({"entry": entry})
        self.assertEqual(
            (
                created.status,
                entry["owner"],
                set(entry["policy_ids"]),
                "role" in entry,
                "doc_types" in entry,
            ),
            (values.STATUS_CREATED, False, {read["id"], write["id"]}, False, False),
            msg=values.MSG_PAE_ENTRY,
            abort_on_fail=False,
            method="POST",
            endpoint=path,
        )
        report = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/access", self.admin
        ).body
        origins = [item["origins"] for item in report if item["user_id"] == user.id]
        expected = [
            {
                "kind": "direct",
                "owner": False,
                "inherit_policies": False,
                "group": None,
                "policies": [read["name"], write["name"]],
            }
        ]
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"/api/projects/{project}", user.headers).status,
                origins,
            ),
            (values.STATUS_OK, [expected]),
            msg=values.MSG_PAE_REPORT,
            abort_on_fail=False,
            method="GET",
            endpoint=f"/api/projects/{project}/access",
        )
        updated = self.bloom.bloom_api_call(
            "PATCH", f"{path}/{entry['id']}", self.admin, json={"policy_ids": [read["id"]]}
        )
        self.assertEqual(
            (updated.status, updated.body["policy_ids"]),
            (values.STATUS_OK, [read["id"]]),
            msg=values.MSG_PAE_UPDATED,
            abort_on_fail=False,
            method="PATCH",
            endpoint=path,
        )

    def bud_an_owner_grant_covers_one_project_and_no_administration(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PAE_PREFIXES[1])["id"]
        other = self.bloom.bloom_api_new_project(self.admin, values.PAE_PREFIXES[2])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "project-owner")
        created = self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{project}/members",
            self.admin,
            json={"user_id": user.id, "owner": True, "policy_ids": []},
        )
        capabilities = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/capabilities", user.headers
        )
        self.assertEqual(
            (created.status, created.body["owner"], capabilities.status, capabilities.body),
            (values.STATUS_CREATED, True, values.STATUS_OK, values.PAE_OWNER_CAPABILITIES),
            msg=values.MSG_PAE_OWNER,
            abort_on_fail=False,
            method="GET",
            endpoint=f"/api/projects/{project}/capabilities",
        )
        reached = [
            self.bloom.bloom_api_call("GET", path, user.headers).status
            for path in (
                f"/api/projects/{other}/capabilities",
                f"/api/projects/{project}",
                f"/api/projects/{other}",
                "/api/groups",
                f"/api/projects/{project}/members",
            )
        ]
        forbidden = values.STATUS_FORBIDDEN
        self.assertEqual(
            reached,
            [forbidden, values.STATUS_OK, forbidden, forbidden, forbidden],
            msg=values.MSG_PAE_OWNER_SCOPE,
            abort_on_fail=False,
        )
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/projects/{project}", user.headers, json={"description": "Owner edit"}
        )
        self.assertEqual(
            edited.status,
            values.STATUS_OK,
            msg=values.MSG_PAE_OWNER_EDIT,
            abort_on_fail=False,
            method="PATCH",
            endpoint=f"/api/projects/{project}",
        )

    def bud_a_content_policy_gives_no_project_capability(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PAE_PREFIXES[3])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "content-only")
        policy = self.bloom.bloom_api_new_policy(self.admin, "All content", values.PAE_EVERYTHING)
        self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{project}/members",
            self.admin,
            json={"user_id": user.id, "policy_ids": [policy["id"]]},
        )
        capabilities = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/capabilities", user.headers
        )
        renamed = self.bloom.bloom_api_call(
            "PATCH", f"/api/projects/{project}", user.headers, json={"name": "Forbidden"}
        )
        self.assertEqual(
            (capabilities.status, capabilities.body, renamed.status),
            (values.STATUS_OK, values.PAE_NO_CAPABILITIES, values.STATUS_FORBIDDEN),
            msg=values.MSG_PAE_CONTENT,
            abort_on_fail=False,
            method="GET",
            endpoint=f"/api/projects/{project}/capabilities",
        )
        administrative = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/capabilities", self.admin
        )
        self.assertEqual(
            (administrative.status, all(administrative.body.values())),
            (values.STATUS_OK, True),
            msg=values.MSG_PAE_ADMIN,
            abort_on_fail=False,
        )

    def bud_the_creator_of_a_project_becomes_its_owner(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "project-creator")
        project = self.bloom.bloom_api_new_project(user.headers, values.PAE_PREFIXES[4])["id"]
        members = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/members", self.admin
        ).body
        entries = [
            (item["owner"], item["policy_ids"]) for item in members if item["user_id"] == user.id
        ]
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"/api/projects/{project}", user.headers).status,
                entries,
                self.bloom.bloom_api_call("GET", "/api/users", user.headers).status,
            ),
            (values.STATUS_OK, [(True, [])], values.STATUS_FORBIDDEN),
            msg=values.MSG_PAE_CREATOR,
            abort_on_fail=False,
        )

    def bud_ambiguous_entries_are_refused_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PAE_PREFIXES[5])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "refused-entry")
        policy = self.bloom.bloom_api_new_policy(self.admin, "Refused entry policy")
        cases = (
            ("a role", {"user_id": user.id, "role": "maintainer"}),
            ("no policy and no owner grant", {"user_id": user.id, "policy_ids": []}),
            (
                "an owner grant and a policy",
                {"user_id": user.id, "owner": True, "policy_ids": [policy["id"]]},
            ),
        )
        for what, body in cases:
            answer = self.bloom.bloom_api_call(
                "POST", f"/api/projects/{project}/members", self.admin, json=body
            )
            self.assertEqual(
                answer.status,
                values.STATUS_UNPROCESSABLE,
                msg=values.MSG_PAE_INVALID.format(what=what),
                abort_on_fail=False,
            )
