"""
* @file     ${tests/api/group_owned_policies.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests policies owned by groups and their separate action and origin scopes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the group-owned policies.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class GroupOwnedPoliciesBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_group_owns_several_policies(self):
        values = self.parameters
        requirements, test_cases = (
            self.bloom.bloom_api_rule_policy(
                self.admin, "Owned requirements", "REQ", write=True
            ).body,
            self.bloom.bloom_api_rule_policy(
                self.admin, "Owned test cases", "TC", approve=True
            ).body,
        )
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/groups",
            self.admin,
            json={"name": "Document control", "policy_ids": [requirements["id"], test_cases["id"]]},
        )
        group = created.body
        self.assertEqual(
            (created.status, set(group["policy_ids"]), group["members"], group["grants"]),
            (values.STATUS_CREATED, {requirements["id"], test_cases["id"]}, [], []),
            msg=values.MSG_GOP_GROUP,
            abort_on_fail=False,
        )
        updated = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/groups/{group['id']}",
            self.admin,
            json={"policy_ids": [requirements["id"]]},
        )
        deleted = self.bloom.bloom_api_call(
            "DELETE", f"/api/policies/{requirements['id']}", self.admin
        )
        self.assertEqual(
            (updated.status, updated.body["policy_ids"], deleted.status),
            (values.STATUS_OK, [requirements["id"]], values.STATUS_CONFLICT),
            msg=values.MSG_GOP_REDUCED,
            abort_on_fail=False,
        )

    def bud_write_and_approve_are_separate_rights(self):
        values = self.parameters
        write, approve = (
            self.bloom.bloom_api_rule_policy(self.admin, "Separate write", "REQ", write=True).body,
            self.bloom.bloom_api_rule_policy(
                self.admin, "Separate approve", "REQ", approve=True
            ).body,
        )
        writes, approves = set(write["rules"]["REQ"]["actions"]), set(
            approve["rules"]["REQ"]["actions"]
        )
        self.assertEqual(
            (
                {"create", "edit"} <= writes,
                writes & {"approve", "review", "delete"},
                {"review", "approve"} <= approves,
                approves & {"create", "edit", "delete"},
            ),
            (True, set(), True, set()),
            msg=values.MSG_GOP_ACTIONS,
            abort_on_fail=False,
        )
        project = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[0])["id"]
        author, signer = self.bloom.bloom_api_new_member(
            self.admin, "separate-author", "maintainer"
        ), self.bloom.bloom_api_new_member(self.admin, "separate-signer", "maintainer")
        self.bloom.bloom_api_admit(self.admin, project, author.id, policy_ids=[write["id"]])
        self.bloom.bloom_api_admit(self.admin, project, signer.id, policy_ids=[approve["id"]])
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            author.headers,
            json={"project_id": project, "title": "Controlled requirement", "status": "Draft"},
        )
        requirement = created.body["id"]
        path = f"/api/artefacts/requirement/{requirement}"
        self.bloom.bloom_api_call(
            "PUT",
            path + "/workflow/assignees",
            self.admin,
            json={"reviewer_id": signer.id, "approver_id": signer.id},
        )
        requested = self.bloom.bloom_api_call(
            "POST", path + "/requests", author.headers, json={"kind": "review"}
        )
        refused = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", author.headers, json={"step": "review"}
        )
        self.assertEqual(
            (created.status, requested.status, refused.status),
            (values.STATUS_CREATED, values.STATUS_CREATED, values.STATUS_FORBIDDEN),
            msg=values.MSG_GOP_AUTHOR,
            abort_on_fail=False,
        )
        denied = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{requirement}", signer.headers, json={"title": "No Write"}
        )
        comment = self.bloom.bloom_api_call(
            "POST", path + "/comments", signer.headers, json={"body": "Reviewed requested content"}
        )
        reviewed = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", signer.headers, json={"step": "review"}
        )
        self.assertEqual(
            (denied.status, denied.body["detail"], comment.status, reviewed.status),
            (
                values.STATUS_FORBIDDEN,
                "Missing permission: edit on REQ.",
                values.STATUS_CREATED,
                values.STATUS_OK,
            ),
            msg=values.MSG_GOP_SIGNER,
            abort_on_fail=False,
        )
        by_author = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", author.headers, json={"step": "approve"}
        )
        approved = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", signer.headers, json={"step": "approve"}
        )
        stored = self.bloom.bloom_api_call("GET", f"/api/requirements/{requirement}", self.admin)
        self.assertEqual(
            (
                by_author.status,
                approved.status,
                approved.body["reviewed_by_id"],
                approved.body["approved_by_id"],
                stored.body["status"],
            ),
            (values.STATUS_FORBIDDEN, values.STATUS_OK, signer.id, signer.id, "Approved"),
            msg=values.MSG_GOP_APPROVED,
            abort_on_fail=False,
        )

    def bud_an_unsupported_approval_is_refused_400(self):
        values = self.parameters
        answer = self.bloom.bloom_api_rule_policy(
            self.admin, "Invalid approval", "STD", approve=True
        )
        self.assertEqual(
            answer.status,
            values.STATUS_BAD_REQUEST,
            msg=values.MSG_GOP_UNSUPPORTED,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/policies",
        )

    def bud_an_assigned_policy_cannot_become_an_app_policy_409(self):
        values = self.parameters
        policy = self.bloom.bloom_api_rule_policy(self.admin, "Assigned scope", "REQ").body
        project = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[1])["id"]
        self.bloom.bloom_api_admit(
            self.admin,
            project,
            self.bloom.bloom_api_new_member(self.admin, "scope-user", "maintainer").id,
            policy_ids=[policy["id"]],
        )
        changed = self.bloom.bloom_api_call(
            "PATCH", f"/api/policies/{policy['id']}", self.admin, json={"scope": "app"}
        )
        unchanged = self.bloom.bloom_api_call("GET", f"/api/policies/{policy['id']}", self.admin)
        self.assertEqual(
            (changed.status, unchanged.status, unchanged.body["scope"]),
            (values.STATUS_CONFLICT, values.STATUS_OK, "document"),
            msg=values.MSG_GOP_SCOPE,
            abort_on_fail=False,
        )

    def bud_all_origins_covers_origins_added_later(self):
        values = self.parameters
        policy = self.bloom.bloom_api_rule_policy(
            self.admin, "Future origins", "REQ", write=True
        ).body
        project = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[2])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "future-origins", "maintainer")
        self.bloom.bloom_api_admit(self.admin, project, user.id, policy_ids=[policy["id"]])
        origin = self.bloom.bloom_api_call(
            "POST", "/api/tags", self.admin, json={"name": "Partner"}
        ).body["id"]
        body = {
            "project_id": project,
            "title": "A newly classified requirement",
            "tag_ids": [origin],
        }
        requirement = self.bloom.bloom_api_call(
            "POST", "/api/requirements", self.admin, json=body
        ).body["id"]
        listed = self.bloom.bloom_api_call(
            "GET", "/api/requirements", user.headers, params={"project_id": project}
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "GET", f"/api/requirements/{requirement}", user.headers
                ).status,
                requirement in {row["id"] for row in listed.body["items"]},
                self.bloom.bloom_api_call(
                    "PATCH",
                    f"/api/requirements/{requirement}",
                    user.headers,
                    json={"title": "Updated classification"},
                ).status,
            ),
            (values.STATUS_OK, True, values.STATUS_OK),
            msg=values.MSG_GOP_ORIGINS,
            abort_on_fail=False,
        )

    def bud_a_project_entry_replaces_inherited_group_policies(self):
        values = self.parameters
        write, read = (
            self.bloom.bloom_api_rule_policy(self.admin, "Inherited write", "REQ", write=True).body,
            self.bloom.bloom_api_rule_policy(self.admin, "Explicit read", "REQ").body,
        )
        user = self.bloom.bloom_api_new_member(self.admin, "override-user", "maintainer")
        group = self.bloom.bloom_api_new_group(self.admin, "Requirements control", [write["id"]])[
            "id"
        ]
        self.bloom.bloom_api_add_group_member(self.admin, group, user.id)
        inherited, explicit = (
            self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[3])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[4])["id"],
        )
        self.bloom.bloom_api_admit(self.admin, inherited, user.id, inherit_policies=True)
        self.bloom.bloom_api_admit(
            self.admin, explicit, user.id, inherit_policies=False, policy_ids=[read["id"]]
        )
        self.bloom.bloom_api_admit_group(self.admin, group, explicit)
        create = lambda project, title: self.bloom.bloom_api_call(
            "POST", "/api/requirements", user.headers, json={"project_id": project, "title": title}
        ).status
        self.assertEqual(
            (create(inherited, "Inherited Write"), create(explicit, "Explicit Read")),
            (values.STATUS_CREATED, values.STATUS_FORBIDDEN),
            msg=values.MSG_GOP_OVERRIDE,
            abort_on_fail=False,
        )
        permissions = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{explicit}/permissions", user.headers
        ).body["REQ"]
        other = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[5])["id"]
        self.assertEqual(
            (
                "create" in permissions,
                self.bloom.bloom_api_call("GET", f"/api/projects/{other}", user.headers).status,
            ),
            (False, values.STATUS_FORBIDDEN),
            msg=values.MSG_GOP_NOT_ADMITTED,
            abort_on_fail=False,
        )

    def bud_an_external_account_keeps_review_only(self):
        values = self.parameters
        policy = self.bloom.bloom_api_rule_policy(
            self.admin, "External ceiling", "REQ", write=True, approve=True, delete=True
        ).body
        project = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[6])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "external-ceiling", "external")
        self.bloom.bloom_api_admit(self.admin, project, user.id, policy_ids=[policy["id"]])
        permissions = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", user.headers
        )
        granted = set(permissions.body["REQ"])
        self.assertEqual(
            (permissions.status, "review" in granted, granted & {"approve", "delete"}),
            (values.STATUS_OK, True, set()),
            msg=values.MSG_GOP_EXTERNAL,
            abort_on_fail=False,
        )
        requirement = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Customer review", "req_origin": "Customer"},
        ).body["id"]
        path = f"/api/artefacts/requirement/{requirement}"
        unassigned = self.bloom.bloom_api_call(
            "POST", path + "/comments", user.headers, json={"body": "Unassigned"}
        )
        assigned = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", self.admin, json={"reviewer_id": user.id}
        )
        comment = self.bloom.bloom_api_call(
            "POST", path + "/comments", user.headers, json={"body": "Customer review"}
        )
        as_approver = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", self.admin, json={"approver_id": user.id}
        )
        self.assertEqual(
            (unassigned.status, assigned.status, comment.status, as_approver.status),
            (
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                values.STATUS_CREATED,
                values.STATUS_UNPROCESSABLE,
            ),
            msg=values.MSG_GOP_EXTERNAL_REVIEW,
            abort_on_fail=False,
        )
        deleted = self.bloom.bloom_api_call(
            "DELETE", f"/api/requirements/{requirement}", user.headers
        )
        hidden = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Internal review", "req_origin": "Internal"},
        ).body["id"]
        refused = self.bloom.bloom_api_call(
            "POST",
            f"/api/artefacts/requirement/{hidden}/comments",
            user.headers,
            json={"body": "Hidden"},
        )
        self.assertEqual(
            (deleted.status, deleted.body["detail"], refused.status),
            (
                values.STATUS_FORBIDDEN,
                "Missing permission: delete on REQ.",
                values.STATUS_NOT_FOUND,
            ),
            msg=values.MSG_GOP_EXTERNAL_LIMITS,
            abort_on_fail=False,
        )

    def bud_all_origins_lends_no_scope_to_a_narrow_write(self):
        values = self.parameters
        read = self.bloom.bloom_api_rule_policy(self.admin, "Broad read rule", "REQ").body
        write = self.bloom.bloom_api_rule_policy(
            self.admin,
            "Narrow write rule",
            "REQ",
            write=True,
            all_origins=False,
            visibility=["customer"],
        ).body
        project = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[7])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "narrow-write", "maintainer")
        self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_ids=[read["id"], write["id"]]
        )
        row = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Internal requirement", "visibility": "internal"},
        ).body["id"]
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"/api/requirements/{row}", user.headers).status,
                self.bloom.bloom_api_call(
                    "PATCH",
                    f"/api/requirements/{row}",
                    user.headers,
                    json={"title": "Scope escalation"},
                ).status,
            ),
            (values.STATUS_OK, values.STATUS_FORBIDDEN),
            msg=values.MSG_GOP_NARROW,
            abort_on_fail=False,
        )

    def bud_a_project_entry_refuses_an_app_policy_400(self):
        values = self.parameters
        body = {
            "name": "User management",
            "scope": "app",
            "rules": {"users": {"read": True, "write": True}},
        }
        policy = self.bloom.bloom_api_call("POST", "/api/policies", self.admin, json=body)
        project = self.bloom.bloom_api_new_project(self.admin, values.GOP_PREFIXES[8])["id"]
        denied = self.bloom.bloom_api_admit(
            self.admin,
            project,
            self.bloom.bloom_api_new_member(self.admin, "app-boundary", "maintainer").id,
            policy_ids=[policy.body["id"]],
        )
        self.assertEqual(
            (policy.status, denied.status),
            (values.STATUS_CREATED, values.STATUS_BAD_REQUEST),
            msg=values.MSG_GOP_APP,
            abort_on_fail=False,
        )
