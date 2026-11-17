"""
* @file     ${tests/api/visions_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Vision document kind, its built-in access and its links.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the visions.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class VisionsHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_product_owners_hold_the_visions_policy(self):
        visions = self.bloom.bloom_api_built_in_policy(self.admin, "Visions")
        groups = {
            group["name"]: group["policy_ids"]
            for group in self.bloom.bloom_api_call("GET", "/api/groups", self.admin).body
        }
        self.assertEqual(
            (
                visions in groups["Product Owners"],
                [visions in groups[name] for name in self.parameters.VISH_OTHER_GROUPS],
            ),
            (True, [False] * 4),
            msg=self.parameters.MSG_VISH_OWNERS,
            abort_on_fail=False,
        )

    def bud_a_vision_is_a_draft_with_its_own_id(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.VISH_PREFIXES[0])
        author = self.bloom.bloom_api_holder(
            self.admin, "vision-author", project["id"], "Visions"
        ).headers
        created = self.bloom.bloom_api_add_typed_document(
            author, project["id"], "VIS", "Vision", "internal"
        )
        vision = created.body
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{vision['id']}", author, json={"title": "Edited vision"}
        )
        self.assertEqual(
            (created.status, vision["doc_id"], vision["doc_type"], vision["status"], edited.status),
            (
                values.STATUS_CREATED,
                f"{project['prefix']}-VIS-001",
                "VIS",
                "Draft",
                values.STATUS_OK,
            ),
            msg=values.MSG_VISH_CREATED,
            abort_on_fail=False,
        )
        docs = f"/api/projects/{project['prefix']}/docs"
        listed = self.bloom.bloom_api_call("GET", docs, author, params={"type": "VIS"})
        detail = self.bloom.bloom_api_call("GET", f"{docs}/visions/{vision['doc_id']}", author)
        self.assertEqual(
            (
                listed.status,
                [item["doc_id"] for item in listed.body["items"]],
                detail.status,
                {"edit", "approve"} <= set(detail.body["allowed_actions"]),
            ),
            (values.STATUS_OK, [vision["doc_id"]], values.STATUS_OK, True),
            msg=values.MSG_VISH_LISTED,
            abort_on_fail=False,
        )

    def bud_built_in_read_and_review_cover_visions(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.VISH_PREFIXES[1])
        internal = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "VIS", "Internal vision", "internal"
        ).body
        customer = self.bloom.bloom_api_add_typed_document(
            self.admin, project["id"], "VIS", "Customer vision", "customer"
        ).body
        docs = f"/api/projects/{project['prefix']}/docs"
        reader = self.bloom.bloom_api_holder(
            self.admin, "vision-reader", project["id"], "Read Internal"
        ).headers
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"/api/documents/{internal['id']}", reader).status,
                self.bloom.bloom_api_call(
                    "PATCH",
                    f"/api/documents/{internal['id']}",
                    reader,
                    json={"title": "Not allowed"},
                ).status,
            ),
            (values.STATUS_OK, values.STATUS_FORBIDDEN),
            msg=values.MSG_VISH_READER,
            abort_on_fail=False,
        )
        reviewer = self.bloom.bloom_api_holder(
            self.admin, "vision-reviewer", project["id"], "Read Internal", "Review Internal"
        ).headers
        detail = self.bloom.bloom_api_call("GET", f"{docs}/visions/{internal['doc_id']}", reviewer)
        self.assertEqual(
            (detail.status, "review" in detail.body["allowed_actions"]),
            (values.STATUS_OK, True),
            msg=values.MSG_VISH_REVIEWER,
            abort_on_fail=False,
        )
        customer_reader = self.bloom.bloom_api_holder(
            self.admin, "vision-customer", project["id"], "Read Customer"
        ).headers
        listed = self.bloom.bloom_api_call("GET", docs, customer_reader, params={"type": "VIS"})
        self.assertEqual(
            (listed.status, [item["doc_id"] for item in listed.body["items"]]),
            (values.STATUS_OK, [customer["doc_id"]]),
            msg=values.MSG_VISH_CUSTOMER,
            abort_on_fail=False,
        )
        spec_only = self.bloom.bloom_api_policy_user(
            self.admin, "spec-only", {"SPEC": ["view"]}, project["id"]
        ).headers
        listed = self.bloom.bloom_api_call("GET", docs, spec_only, params={"type": "VIS"})
        read = self.bloom.bloom_api_call(
            "GET", f"/api/documents/{internal['id']}", spec_only
        ).status
        self.assertEqual(
            (
                listed.status,
                listed.body["items"],
                read in (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND),
            ),
            (values.STATUS_OK, [], True),
            msg=values.MSG_VISH_SPEC_ONLY,
            abort_on_fail=False,
        )

    def bud_vision_links_follow_their_rules(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.VISH_PREFIXES[2])
        ids = {
            "vision": self.bloom.bloom_api_add_typed_document(
                self.admin, project["id"], "VIS", "Vision", "internal"
            ).body["id"],
            "spec": self.bloom.bloom_api_add_typed_document(
                self.admin, project["id"], "SPEC", "Specification", "internal"
            ).body["id"],
            "standard": self.bloom.bloom_api_add_typed_document(
                self.admin, project["id"], "STD", "Standard", "internal"
            ).body["id"],
        }
        for kind in ("requirements", "changes", "risks", "designs"):
            ids[kind] = self.bloom.bloom_api_call(
                "POST",
                f"/api/{kind}",
                self.admin,
                json={"project_id": project["id"], "title": kind},
            ).body["id"]

        def link(source_type, source, target_type, target, role):
            body = {
                "project_id": project["id"],
                "source_type": source_type,
                "source_id": ids[source],
                "target_type": target_type,
                "target_id": ids[target],
                "role": role,
            }
            return self.bloom.bloom_api_call("POST", "/api/links", self.admin, json=body).status

        for case in values.VISH_ALLOWED_LINKS:
            self.assertEqual(
                link(*case),
                values.STATUS_CREATED,
                msg=values.MSG_VISH_LINK_ALLOWED.format(
                    source=case[0], target=case[2], role=case[4]
                ),
                abort_on_fail=False,
            )
        for case in values.VISH_REFUSED_LINKS:
            self.assertIn(
                link(*case),
                (values.STATUS_BAD_REQUEST, values.STATUS_UNPROCESSABLE),
                msg=values.MSG_VISH_LINK_REFUSED.format(
                    source=case[0], target=case[2], role=case[4]
                ),
                abort_on_fail=False,
            )

    def bud_product_owners_and_released_maintainers_author_visions(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.VISH_PREFIXES[3])
        groups = {
            group["name"]: group["id"]
            for group in self.bloom.bloom_api_call("GET", "/api/groups", self.admin).body
        }
        released = [
            self.bloom.bloom_api_built_in_policy(self.admin, name)
            for name in (*values.VISH_RELEASED_MAINTAINER_SET, "Visions")
        ]
        assignments = (
            ("product owner", {"policy_group_id": groups["Product Owners"]}),
            ("released maintainer", {"policy_ids": released}),
        )
        for who, assignment in assignments:
            user = self.bloom.bloom_api_new_member(self.admin, who.replace(" ", "-"))
            member = self.bloom.bloom_api_call(
                "POST",
                f"/api/projects/{project['id']}/members",
                self.admin,
                json={"user_id": user.id, **assignment},
            )
            created = self.bloom.bloom_api_add_typed_document(
                user.headers, project["id"], "VIS", who
            )
            edited = self.bloom.bloom_api_call(
                "PATCH",
                f"/api/documents/{created.body['id']}",
                user.headers,
                json={"title": f"{who} edit"},
            )
            self.assertEqual(
                (member.status, created.status, edited.status),
                (values.STATUS_CREATED, values.STATUS_CREATED, values.STATUS_OK),
                msg=values.MSG_VISH_AUTHOR.format(who=who),
                abort_on_fail=False,
            )

    def bud_a_review_internal_holder_reviews_a_vision(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.VISH_PREFIXES[4])
        author = self.bloom.bloom_api_holder(self.admin, "review-author", project["id"], "Visions")
        reviewer = self.bloom.bloom_api_holder(
            self.admin, "review-reviewer", project["id"], "Read Internal", "Review Internal"
        )
        approver = self.bloom.bloom_api_holder(
            self.admin, "review-approver", project["id"], "Visions"
        )
        vision = self.bloom.bloom_api_add_typed_document(
            author.headers, project["id"], "VIS", "Reviewed vision"
        ).body["id"]
        path = f"/api/artefacts/document/{vision}"
        assignees = {"reviewer_id": reviewer.id, "approver_id": approver.id}
        answers = (
            self.bloom.bloom_api_call(
                "PUT", path + "/workflow/assignees", author.headers, json=assignees
            ).status,
            self.bloom.bloom_api_call(
                "POST", path + "/requests", author.headers, json={"kind": "review"}
            ).status,
            self.bloom.bloom_api_call(
                "POST", path + "/comments", reviewer.headers, json={"body": "Reviewed the vision"}
            ).status,
            self.bloom.bloom_api_call(
                "POST", path + "/requests", reviewer.headers, json={"kind": "approval"}
            ).status,
        )
        self.assertEqual(
            answers,
            (values.STATUS_OK, values.STATUS_CREATED, values.STATUS_CREATED, values.STATUS_CREATED),
            msg=values.MSG_VISH_REVIEW,
            abort_on_fail=False,
        )
