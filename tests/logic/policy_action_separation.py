"""
* @file     ${tests/logic/policy_action_separation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that each permission field grants only its own operations.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the policy action separation.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class PolicyActionSeparationBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_write_cannot_approve_or_delete(self):
        actions = self.bloom.bloom_actions_for_rule("REQ", True, True)
        self.print_variables({"actions": sorted(actions)})
        self.assertEqual(
            ({"create", "edit", "view"} <= actions, {"review", "approve", "delete"} & actions),
            (True, set()),
            msg=self.parameters.MSG_PAS_WRITE,
            abort_on_fail=False,
        )

    def bud_approval_and_deletion_do_not_add_read_or_write(self):
        actions = self.bloom.bloom_actions_for_rule("REQ", False, False, True, approve=True)
        self.assertEqual(
            actions,
            {"review", "approve", "delete"},
            msg=self.parameters.MSG_PAS_APPROVE,
            abort_on_fail=False,
        )

    def bud_write_includes_read_without_approve_or_delete(self):
        actions = self.bloom.bloom_actions_for_rule("REQ", False, True)
        self.assertEqual(
            (
                {"view", "comment", "create", "edit"} <= actions,
                {"approve", "review", "delete"} & actions,
            ),
            (True, set()),
            msg=self.parameters.MSG_PAS_WRITE_READ,
            abort_on_fail=False,
        )

    def bud_a_stored_edit_reads_as_view_comment_and_edit(self):
        matrix = {"REQ": ["edit"]}
        self.assertEqual(
            (
                self.bloom.bloom_actions_on(matrix, "REQ"),
                self.bloom.bloom_rule_of(["edit"]),
                self.bloom.bloom_has_permission(matrix, "view", "REQ"),
                self.bloom.bloom_has_permission(matrix, "view", "TC"),
                self.bloom.bloom_has_permission(matrix, "approve", "REQ"),
                matrix,
            ),
            (
                {"view", "comment", "edit"},
                (True, True, False, False, False),
                True,
                False,
                False,
                {"REQ": ["edit"]},
            ),
            msg=self.parameters.MSG_PAS_STORED,
            abort_on_fail=False,
        )

    def bud_review_is_independent_on_every_document_type(self):
        for resource in self.bloom.bloom_permission_resources_of_documents():
            actions = sorted(self.bloom.bloom_actions_for_rule(resource, False, False, review=True))
            matrix = {resource: actions}
            granted = [
                a
                for a in self.parameters.PAS_OTHER_ACTIONS
                if self.bloom.bloom_has_permission(matrix, a, resource)
            ]
            self.assertEqual(
                (actions, self.bloom.bloom_has_permission(matrix, "review", resource), granted),
                (["review"], True, []),
                msg=self.parameters.MSG_PAS_REVIEW.format(resource=resource),
                abort_on_fail=False,
            )

    def bud_a_review_rule_roundtrips_as_review_only(self):
        stored, flags, again = self.bloom.bloom_review_rule_roundtrip()
        self.print_variables({"stored": stored, "flags": flags})
        self.assertEqual(
            (stored, flags, again),
            (
                (
                    {"REQ": ["review"]},
                    {"REQ": {"all": False, "visibility": ["customer"], "tags": []}},
                ),
                (True, False, False, False, False),
                {"REQ": ["review"]},
            ),
            msg=self.parameters.MSG_PAS_ROUNDTRIP,
            abort_on_fail=False,
        )

    def bud_a_review_rule_requires_an_origin(self):
        detail = self.bloom.bloom_validate_rule("REQ", review=True)
        self.print_variables({"refusal": detail})
        self.assertIn(
            "Choose at least one tag for REQ",
            detail or "",
            msg=self.parameters.MSG_PAS_ORIGIN,
            abort_on_fail=False,
        )

    def bud_review_is_not_a_project_or_application_operation(self):
        for resource in self.parameters.PAS_PROJECT_RESOURCES:
            detail = self.bloom.bloom_validate_rule(resource, "app", review=True)
            self.assertIn(
                f"Review is not supported on {resource}",
                detail or "",
                msg=self.parameters.MSG_PAS_PROJECT.format(resource=resource),
                abort_on_fail=False,
            )

    def bud_approval_is_refused_where_it_is_not_supported(self):
        for resource in self.parameters.PAS_NO_APPROVAL:
            detail = self.bloom.bloom_validate_rule(resource, approve=True, all_origins=True)
            self.assertIn(
                f"Approve is not supported on {resource}",
                detail or "",
                msg=self.parameters.MSG_PAS_EXCEPTION.format(resource=resource),
                abort_on_fail=False,
            )

    def bud_external_readers_may_review_but_not_approve_or_delete(self):
        denied = self.bloom.bloom_external_denied_actions()
        self.assertEqual(
            ("review" in denied, {"approve", "delete"} <= denied),
            (False, True),
            msg=self.parameters.MSG_PAS_EXTERNAL,
            abort_on_fail=False,
        )

    def bud_write_and_approval_add_no_review(self):
        for resource in self.parameters.PAS_NO_EXTRA_REVIEW:
            actions = self.bloom.bloom_actions_for_rule(resource, True, True, True, approve=True)
            self.assertNotIn(
                "review",
                actions,
                msg=self.parameters.MSG_PAS_NO_EXTRA.format(resource=resource),
                abort_on_fail=False,
            )

    def bud_an_external_review_term_keeps_the_customer_scope(self):
        terms = self.bloom.bloom_external_review_terms(
            {"STD": ["review", "approve", "delete"]},
            {"STD": {"all": True, "visibility": [], "tags": []}},
        )
        self.print_variables({"terms": terms})
        self.assertEqual(
            terms,
            [({"STD": {"review"}}, True, frozenset({"STD"}))],
            msg=self.parameters.MSG_PAS_TERM,
            abort_on_fail=False,
        )
