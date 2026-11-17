"""
* @file     ${tests/api/user_access_summary.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the summary of a user's groups and project access.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the user access summary.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class UserAccessSummaryBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_summary_lists_groups_and_projects(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "summarised")
        policy = self.bloom.bloom_api_new_policy(self.admin, "Summary policy")
        granted, other, bundle = (
            self.bloom.bloom_api_new_group(self.admin, name, [policy["id"]])
            for name in ("Granted team", "Other team", "Bundle")
        )
        for group in (granted, other):
            self.bloom.bloom_api_add_group_member(self.admin, group["id"], user.id)
        via_group, via_bundle, owned = (
            self.bloom.bloom_api_new_project(self.admin, prefix)
            for prefix in values.UAS_PREFIXES[:3]
        )
        self.bloom.bloom_api_admit_group(self.admin, granted["id"], via_group["id"])
        self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{via_bundle['id']}/members",
            self.admin,
            json={"user_id": user.id, "policy_group_id": bundle["id"]},
        )
        self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{owned['id']}/members",
            self.admin,
            json={"user_id": user.id, "owner": True, "policy_ids": []},
        )
        answer = self.bloom.bloom_api_call(
            "GET", f"/api/users/{user.id}/access-summary", self.admin
        )
        self.print_variables({"summary": answer.body})
        teams = sorted([granted["name"], other["name"]])
        row = lambda project, owner, groups: {
            "project_id": project["id"],
            "project_name": project["name"],
            "owner": owner,
            "groups": groups,
            "direct": False,
        }
        self.assertEqual(
            (answer.status, answer.body),
            (
                values.STATUS_OK,
                {
                    "every_project": False,
                    "groups": teams,
                    "projects": [
                        row(via_group, False, teams),
                        row(via_bundle, False, [bundle["name"]]),
                        row(owned, True, []),
                    ],
                },
            ),
            msg=values.MSG_UAS_SUMMARY,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/users/{id}/access-summary",
        )
        self.assertNotIn(
            policy["name"], str(answer.body), msg=values.MSG_UAS_NO_POLICY, abort_on_fail=False
        )

    def bud_direct_policies_are_labelled_direct(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "direct-summary")
        project = self.bloom.bloom_api_new_project(self.admin, values.UAS_PREFIXES[3])["id"]
        policy = self.bloom.bloom_api_new_policy(self.admin, "Direct summary policy")
        self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{project}/members",
            self.admin,
            json={"user_id": user.id, "policy_ids": [policy["id"]]},
        )
        projects = self.bloom.bloom_api_call(
            "GET", f"/api/users/{user.id}/access-summary", self.admin
        ).body["projects"]
        self.assertEqual(
            [(item["project_id"], item["groups"], item["direct"]) for item in projects],
            [(project, [], True)],
            msg=values.MSG_UAS_DIRECT,
            abort_on_fail=False,
        )

    def bud_no_access_is_empty_and_an_administrator_has_every_project(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "no-access")
        other_admin = self.bloom.bloom_api_new_member(self.admin, "second-admin", role="admin")
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "GET", f"/api/users/{user.id}/access-summary", self.admin
                ).body,
                self.bloom.bloom_api_call(
                    "GET", f"/api/users/{other_admin.id}/access-summary", self.admin
                ).body["every_project"],
            ),
            ({"every_project": False, "groups": [], "projects": []}, True),
            msg=values.MSG_UAS_EMPTY,
            abort_on_fail=False,
        )

    def bud_the_summary_is_for_administrators_only(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "curious")
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "GET", f"/api/users/{user.id}/access-summary", user.headers
                ).status,
                self.bloom.bloom_api_call(
                    "GET", f"/api/users/{999999}/access-summary", self.admin
                ).status,
            ),
            (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND),
            msg=values.MSG_UAS_ADMIN_ONLY,
            abort_on_fail=False,
        )
