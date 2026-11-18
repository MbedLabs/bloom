"""
* @file     ${tests/api/project_member_retention.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that removing project access keeps the account and its contributions.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the member retention.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectMemberRetentionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_removing_and_restoring_access_keeps_every_contribution(self):
        values = self.parameters
        for assignment in values.RET_ASSIGNMENTS:
            admin, author = self.bloom.bloom_new_retention_world()
            policy = self.bloom.bloom_add_record("Policy", **values.RET_POLICY)
            group = self.bloom.bloom_api_new_group(admin, "Contributors", [policy])["id"]

            def assign(project_id):
                if assignment == "bundle":
                    body = {"project_id": project_id, "user_ids": [2]}
                    return self.bloom.bloom_api_call(
                        "POST", f"/api/groups/{group}/assignments", admin, json=body
                    ).body[0]
                body = {"user_id": 2, "policy_ids": [policy]}
                return self.bloom.bloom_api_call(
                    "POST", f"/api/projects/{project_id}/members", admin, json=body
                ).body

            membership, other_membership = assign(1), assign(2)
            requirement, document = self.bloom.bloom_add_authored_content(1, 2, 1)
            excluded = ("audit_events", "project_access", "project_access_policies")
            before = self.bloom.bloom_stored_rows(excluded)
            reads = lambda: (
                self.bloom.bloom_api_call("GET", "/api/projects/1", author).status,
                self.bloom.bloom_api_call("GET", f"/api/requirements/{requirement}", author).status,
            )
            self.assertEqual(
                reads(),
                (values.STATUS_OK, values.STATUS_OK),
                msg=values.MSG_RET_BEFORE.format(assignment=assignment),
                abort_on_fail=False,
            )
            removed = self.bloom.bloom_api_call(
                "DELETE", f"/api/projects/1/members/{membership['id']}", admin
            )
            self.assertEqual(
                (
                    removed.status,
                    reads(),
                    self.bloom.bloom_api_call("GET", "/api/projects/2", author).status,
                    self.bloom.bloom_api_call("GET", "/api/projects/2/members", admin).body,
                ),
                (
                    values.STATUS_NO_CONTENT,
                    (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND),
                    values.STATUS_OK,
                    [other_membership],
                ),
                msg=values.MSG_RET_REMOVED,
                abort_on_fail=False,
                method="DELETE",
                endpoint="/api/projects/1/members/{id}",
            )
            self.assertTrue(
                self.bloom.bloom_stored_rows(excluded) == before,
                msg=values.MSG_RET_ROWS.format(assignment=assignment),
                abort_on_fail=False,
            )
            options = self.bloom.bloom_api_call("GET", "/api/groups/assignment-options", admin).body
            offered = [
                person["id"]
                for person in options["users"]
                if person["email"] == "author@example.com"
            ]
            self.assertEqual(offered, [2], msg=values.MSG_RET_OPTION, abort_on_fail=False)
            restored = assign(1)
            content = self.bloom.bloom_api_call("GET", f"/api/requirements/{requirement}", author)
            attachments = self.bloom.bloom_api_call(
                "GET", f"/api/documents/{document}/attachments", author
            ).body
            self.assertEqual(
                (
                    restored["user_id"],
                    membership["user_id"],
                    content.status,
                    content.body["title"],
                    attachments[0]["uploaded_by_id"],
                    self.bloom.bloom_stored_rows(excluded) == before,
                ),
                (2, 2, values.STATUS_OK, "Authored content", 2, True),
                msg=values.MSG_RET_RESTORED,
                abort_on_fail=False,
            )
