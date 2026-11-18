"""
* @file     ${tests/api/project_policy_grants.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests group policies and explicit project entries with their complete rules.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project policy grants.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectPolicyGrantsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_policy_answers_with_its_rules_and_tags(self):
        values = self.parameters
        policy = self.bloom.bloom_api_new_policy(
            self.admin, "Customer read", visibility="customer", types=["REQ"]
        )
        copy = self.bloom.bloom_api_call(
            "POST", f"/api/policies/{policy['id']}/duplicate", self.admin
        )
        self.assertEqual(
            (policy["rules"], "base_role" in policy, copy.status, copy.body["rules"]),
            (
                values.PPG_CUSTOMER_READ_RULES,
                False,
                values.STATUS_CREATED,
                values.PPG_CUSTOMER_READ_RULES,
            ),
            msg=values.MSG_PPG_CONTRACT,
            abort_on_fail=False,
        )

    def bud_group_policies_apply_on_the_granted_project_only(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "granted-member")
        project, other = (
            self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[0])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[1])["id"],
        )
        read = self.bloom.bloom_api_new_policy(self.admin, "Granted read", types=["REQ"])
        write = self.bloom.bloom_api_new_policy(
            self.admin, "Granted write", values.PPG_TC_WRITE, types=["TC"]
        )
        group = self.bloom.bloom_api_new_group(
            self.admin, "Granted team", [read["id"], write["id"]]
        )
        self.bloom.bloom_api_add_group_member(self.admin, group["id"], user.id)
        granted = self.bloom.bloom_api_call(
            "POST", f"/api/groups/{group['id']}/grants", self.admin, json={"project_id": project}
        )
        grant = granted.body["grants"][0]
        self.assertEqual(
            (
                "policy_id" in group,
                granted.status,
                grant["project_id"],
                "policy_ids" in grant,
                set(granted.body["policy_ids"]),
            ),
            (False, values.STATUS_CREATED, project, False, {read["id"], write["id"]}),
            msg=values.MSG_PPG_GROUP,
            abort_on_fail=False,
        )
        rights = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", user.headers
        ).body
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"/api/projects/{project}", user.headers).status,
                self.bloom.bloom_api_call("GET", f"/api/projects/{other}", user.headers).status,
                rights["REQ"],
                set(rights["TC"]),
            ),
            (
                values.STATUS_OK,
                values.STATUS_FORBIDDEN,
                ["comment", "view"],
                self.bloom.bloom_resource_actions_of("TC") - {"delete", "review", "approve"},
            ),
            msg=values.MSG_PPG_REACH,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_api_call("DELETE", f"/api/policies/{write['id']}", self.admin).status,
            values.STATUS_CONFLICT,
            msg=values.MSG_PPG_IN_USE,
            abort_on_fail=False,
        )
        updated = self.bloom.bloom_api_call(
            "PATCH", f"/api/groups/{group['id']}", self.admin, json={"policy_ids": [read["id"]]}
        )
        after = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", user.headers
        ).body
        self.assertEqual(
            (updated.status, updated.body["policy_ids"], "TC" in after),
            (values.STATUS_OK, [read["id"]], False),
            msg=values.MSG_PPG_REDUCED,
            abort_on_fail=False,
        )
        revoked = self.bloom.bloom_api_call(
            "DELETE", f"/api/groups/{group['id']}/grants/{grant['id']}", self.admin
        ).status
        self.assertEqual(
            (
                revoked,
                self.bloom.bloom_api_call("GET", f"/api/projects/{project}", user.headers).status,
            ),
            (values.STATUS_NO_CONTENT, values.STATUS_FORBIDDEN),
            msg=values.MSG_PPG_REVOKED,
            abort_on_fail=False,
        )

    def bud_a_grant_selecting_policies_is_refused_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[2])["id"]
        policy = self.bloom.bloom_api_new_policy(self.admin, "Admission policy")
        group = self.bloom.bloom_api_new_group(self.admin, "Admission team")
        cases = (
            ("without a project", {"project_id": None, "policy_ids": [policy["id"]]}),
            ("with an empty policy list", {"project_id": project, "policy_ids": []}),
            (
                "that does not inherit the group policies",
                {"project_id": project, "inherit_policies": False},
            ),
        )
        for what, body in cases:
            answer = self.bloom.bloom_api_call(
                "POST", f"/api/groups/{group['id']}/grants", self.admin, json=body
            )
            self.assertEqual(
                answer.status,
                values.STATUS_UNPROCESSABLE,
                msg=values.MSG_PPG_ADMISSION.format(what=what),
                abort_on_fail=False,
            )
        legacy = self.bloom.bloom_api_call(
            "POST",
            "/api/groups",
            self.admin,
            json={"name": "Legacy team", "policy_id": policy["id"]},
        )
        grants = self.bloom.bloom_api_call("GET", f"/api/groups/{group['id']}", self.admin).body[
            "grants"
        ]
        self.assertEqual(
            (legacy.status, grants),
            (values.STATUS_UNPROCESSABLE, []),
            msg=values.MSG_PPG_LEGACY,
            abort_on_fail=False,
        )

    def bud_creating_borrows_no_visibility_from_another_policy(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "whole-create")
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[3])["id"]
        read = self.bloom.bloom_api_new_policy(self.admin, "Whole read")
        write = self.bloom.bloom_api_new_policy(
            self.admin, "Customer create", {"REQ": ["view", "create"]}, "customer"
        )
        self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_ids=[read["id"], write["id"]]
        )
        create = lambda title, origin: self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            user.headers,
            json={"project_id": project, "title": title, "req_origin": origin},
        )
        denied, allowed = create("Denied internal creation", "Internal"), create(
            "Allowed customer creation", "Customer"
        )
        self.assertEqual(
            (denied.status, allowed.status, allowed.body["visibility"]),
            (values.STATUS_FORBIDDEN, values.STATUS_CREATED, "customer"),
            msg=values.MSG_PPG_CREATE,
            abort_on_fail=False,
        )
        rows = self.bloom.bloom_api_call(
            "GET", "/api/requirements", self.admin, params={"project_id": project}
        ).body["items"]
        self.assertEqual(
            [row["title"] for row in rows],
            ["Allowed customer creation"],
            msg=values.MSG_PPG_CREATED_ROWS,
            abort_on_fail=False,
        )

    def bud_invalid_policy_rules_are_refused_400(self):
        values = self.parameters
        for number, (rules, detail) in enumerate(values.PPG_INVALID_RULES):
            answer = self.bloom.bloom_api_call(
                "POST",
                "/api/policies",
                self.admin,
                json={"name": f"Invalid rules {number}", "rules": rules},
            )
            self.assertEqual(
                (answer.status, detail in answer.body["detail"]),
                (values.STATUS_BAD_REQUEST, True),
                msg=values.MSG_PPG_RULES.format(detail=detail),
                abort_on_fail=False,
            )

    def bud_approval_needs_a_policy_covering_the_row(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "scoped-approver")
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[4])["id"]
        reader = self.bloom.bloom_api_new_policy(self.admin, "Approval reader")
        writer = self.bloom.bloom_api_new_policy(
            self.admin, "Customer approver", {"REQ": ["view", "create", "approve"]}, "customer"
        )
        self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_ids=[reader["id"], writer["id"]]
        )
        admin_id = self.bloom.bloom_api_call("GET", "/api/auth/me", self.admin).body["id"]
        rows = (
            ("internal", self.admin, "Internal", values.STATUS_FORBIDDEN, "Review"),
            ("customer", user.headers, "Customer", values.STATUS_OK, "Approved"),
        )
        for origin, creator, req_origin, status, state in rows:
            body = {
                "project_id": project,
                "title": f"{req_origin} approval",
                "req_origin": req_origin,
                "reviewer_id": admin_id,
            }
            created = self.bloom.bloom_api_call(
                "POST", "/api/requirements", creator, json=body
            ).body["id"]
            base = f"/api/artefacts/requirement/{created}"
            self.bloom.bloom_api_call("POST", base + "/requests", creator, json={"kind": "review"})
            self.bloom.bloom_api_call(
                "POST", base + "/comments", self.admin, json={"body": "Reviewed revision"}
            )
            self.bloom.bloom_api_call(
                "POST", base + "/requests", self.admin, json={"kind": "approval"}
            )
            decided = self.bloom.bloom_api_call(
                "POST", base + "/sign-off", user.headers, json={"step": "approve"}
            )
            stored = self.bloom.bloom_api_call(
                "GET", f"/api/requirements/{created}", self.admin
            ).body["status"]
            self.assertEqual(
                (decided.status, stored),
                (status, state),
                msg=values.MSG_PPG_APPROVAL.format(origin=origin, status=status, state=state),
                abort_on_fail=False,
            )

    def bud_a_new_reviewer_must_see_the_artefact_422(self):
        values = self.parameters
        reviewer = self.bloom.bloom_api_new_member(self.admin, "scoped-reviewer")
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[5])["id"]
        review = self.bloom.bloom_api_new_policy(
            self.admin, "Customer review", {"REQ": ["view", "review"]}, "customer"
        )
        self.bloom.bloom_api_admit(self.admin, project, reviewer.id, policy_ids=[review["id"]])
        create = lambda origin: self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={
                "project_id": project,
                "title": f"{origin} assignment",
                "req_origin": origin,
                "reviewer_id": reviewer.id,
            },
        ).status
        self.assertEqual(
            (create("Internal"), create("Customer")),
            (values.STATUS_UNPROCESSABLE, values.STATUS_CREATED),
            msg=values.MSG_PPG_ASSIGNEE,
            abort_on_fail=False,
        )

    def bud_a_reassignment_checks_the_proposed_visibility_422(self):
        values = self.parameters
        reviewer = self.bloom.bloom_api_new_member(self.admin, "reassigned-reviewer")
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[6])["id"]
        review = self.bloom.bloom_api_new_policy(
            self.admin, "Reassignment review", {"REQ": ["view", "review"]}, "customer"
        )
        self.bloom.bloom_api_admit(self.admin, project, reviewer.id, policy_ids=[review["id"]])
        for origin in ("Internal", "Customer"):
            row = self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": f"Assign {origin}", "req_origin": origin},
            ).body["id"]
            denied = self.bloom.bloom_api_call(
                "PATCH",
                f"/api/requirements/{row}",
                self.admin,
                json={"reviewer_id": reviewer.id, "req_origin": "Internal"},
            )
            stored = self.bloom.bloom_api_call("GET", f"/api/requirements/{row}", self.admin).body
            self.assertEqual(
                (denied.status, stored["reviewer_id"], stored["req_origin"]),
                (values.STATUS_UNPROCESSABLE, None, origin),
                msg=values.MSG_PPG_REASSIGN.format(origin=origin.lower()),
                abort_on_fail=False,
            )

    def bud_a_defect_reviewer_can_be_configured(self):
        values = self.parameters
        reviewer = self.bloom.bloom_api_new_member(self.admin, "defect-reviewer")
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[7])["id"]
        review = self.bloom.bloom_api_new_policy(
            self.admin, "Defect review", {"DEF": ["view", "review"]}
        )
        self.bloom.bloom_api_admit(self.admin, project, reviewer.id, policy_ids=[review["id"]])
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/defects",
            self.admin,
            json={"project_id": project, "title": "Reviewed defect", "reviewer_id": reviewer.id},
        )
        self.assertEqual(
            created.status, values.STATUS_CREATED, msg=values.MSG_PPG_DEFECT, abort_on_fail=False
        )

    def bud_links_need_link_read_and_are_filtered_by_origin(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PPG_PREFIXES[8])["id"]
        case = self.bloom.bloom_api_add_test_case(
            self.admin, project, "Case", visibility="customer"
        ).body["id"]
        links = []
        for origin in ("Customer", "Internal"):
            requirement = self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": f"End {origin}", "req_origin": origin},
            ).body["id"]
            links.append(
                self.bloom.bloom_api_verify(self.admin, project, case, requirement).body["id"]
            )
        for link_read in (True, False):
            user = self.bloom.bloom_api_new_member(self.admin, f"link-reader-{link_read}".lower())
            matrix = {"REQ": ["view"], "TC": ["view"], **({"link": ["view"]} if link_read else {})}
            policy = self.bloom.bloom_api_new_policy(
                self.admin, f"Link scope {link_read}", matrix, "customer"
            )
            self.bloom.bloom_api_admit(self.admin, project, user.id, policy_ids=[policy["id"]])
            answer = self.bloom.bloom_api_call(
                "GET", "/api/links", user.headers, params={"project_id": project}
            )
            status = values.STATUS_OK if link_read else values.STATUS_FORBIDDEN
            how = "with" if link_read else "without"
            self.assertEqual(
                answer.status,
                status,
                msg=values.MSG_PPG_LINKS.format(how=how, status=status),
                abort_on_fail=False,
                method="GET",
                endpoint="/api/links",
            )
            if link_read:
                self.assertEqual(
                    [row["id"] for row in answer.body],
                    links[:1],
                    msg=values.MSG_PPG_LINK_ROWS,
                    abort_on_fail=False,
                )
