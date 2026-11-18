"""
* @file     ${tests/logic/auth_user_workflows.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests deleting users, password resets and role changes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the account workflows.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AuthUserWorkflowsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_deleting_a_user_cleans_its_references_first(self):
        values = self.parameters
        outcome = self.bloom.bloom_delete_user_on_a_recording_session()
        for table in values.AUW_CLEANED_TABLES:
            self.assertTrue(
                any(table in statement for statement in outcome.statements),
                msg=values.MSG_AUW_CLEANED.format(table=table),
                abort_on_fail=False,
            )
        doc_types = [
            i for i, text in enumerate(outcome.statements) if "project_external_doc_types" in text
        ]
        memberships = [
            i
            for i, text in enumerate(outcome.statements)
            if "project_memberships" in text and "project_external_doc_types" not in text
        ]
        self.assertTrue(
            bool(doc_types and memberships) and doc_types[0] < memberships[0],
            msg=values.MSG_AUW_ORDER,
            abort_on_fail=False,
        )
        self.assertEqual(
            (outcome.deleted, outcome.flushes),
            ([True], 1),
            msg=values.MSG_AUW_DELETED,
            abort_on_fail=False,
        )

    def bud_an_administrator_cannot_delete_their_own_account_400(self):
        values = self.parameters
        outcome = self.bloom.bloom_delete_user_on_a_recording_session(own_account=True)
        self.assertEqual(
            (outcome.refusal, len(outcome.statements), outcome.deleted),
            ((values.STATUS_BAD_REQUEST, values.AUW_SELF_DELETE), 1, []),
            msg=values.MSG_AUW_SELF,
            abort_on_fail=False,
        )

    def bud_a_blocked_delete_is_a_conflict_409(self):
        values = self.parameters
        outcome = self.bloom.bloom_delete_user_on_a_recording_session(blocked=True)
        self.assertEqual(
            (outcome.refusal, outcome.deleted),
            ((values.STATUS_CONFLICT, values.AUW_STILL_REFERENCED), []),
            msg=values.MSG_AUW_CONFLICT,
            abort_on_fail=False,
        )

    def bud_a_reset_request_for_a_known_account_sends_one_mail(self):
        self.assertEqual(
            self.bloom.bloom_request_password_reset_on_a_recording_session(known=True),
            (self.parameters.AUW_GENERIC_ANSWER, 1, 1, 1),
            msg=self.parameters.MSG_AUW_KNOWN,
            abort_on_fail=False,
        )

    def bud_a_reset_request_for_an_unknown_account_answers_the_same(self):
        self.assertEqual(
            self.bloom.bloom_request_password_reset_on_a_recording_session(known=False),
            (self.parameters.AUW_GENERIC_ANSWER, 0, 0, 0),
            msg=self.parameters.MSG_AUW_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_a_reset_stores_the_password_and_ends_the_sessions(self):
        values = self.parameters
        outcome = self.bloom.bloom_reset_password_on_a_recording_session(values.AUW_NEW_PASSWORD)
        self.assertEqual(
            (
                outcome.message,
                outcome.password_stored,
                outcome.password_dated,
                outcome.session_version,
                outcome.claims,
                outcome.ended_tokens_of_user,
                outcome.flushes,
            ),
            (values.AUW_RESET_ANSWER, True, True, 2, 1, [True], 1),
            msg=values.MSG_AUW_RESET,
            abort_on_fail=False,
        )

    def bud_a_reset_with_a_bad_token_is_refused_400(self):
        values = self.parameters
        for detail in values.AUW_TOKEN_ERRORS:
            outcome = self.bloom.bloom_reset_password_on_a_recording_session(
                values.AUW_NEW_PASSWORD, token_error=detail
            )
            self.assertEqual(
                (outcome.refusal, outcome.reads, outcome.flushes),
                ((values.STATUS_BAD_REQUEST, detail), 0, 0),
                msg=values.MSG_AUW_BAD_TOKEN.format(detail=detail),
                abort_on_fail=False,
            )

    def bud_the_initial_administrator_promotes_a_user(self):
        outcome = self.bloom.bloom_change_role_on_a_recording_session(
            "maintainer", "admin", by_initial_admin=True
        )
        self.assertEqual(
            (outcome.answered, outcome.stored),
            ("admin", "admin"),
            msg=self.parameters.MSG_AUW_PROMOTE,
            abort_on_fail=False,
        )

    def bud_another_administrator_cannot_promote_403(self):
        values = self.parameters
        outcome = self.bloom.bloom_change_role_on_a_recording_session(
            "maintainer", "admin", by_initial_admin=False
        )
        self.assertEqual(
            (outcome.refusal, outcome.stored),
            ((values.STATUS_FORBIDDEN, values.AUW_PROMOTION_REFUSED), "maintainer"),
            msg=values.MSG_AUW_PROMOTE_REFUSED,
            abort_on_fail=False,
        )

    def bud_an_administrator_role_cannot_be_changed_400(self):
        values = self.parameters
        outcome = self.bloom.bloom_change_role_on_a_recording_session(
            "admin", "maintainer", by_initial_admin=True
        )
        self.assertEqual(
            (outcome.refusal, outcome.stored),
            ((values.STATUS_BAD_REQUEST, values.AUW_DEMOTION_REFUSED), "admin"),
            msg=values.MSG_AUW_DEMOTE_REFUSED,
            abort_on_fail=False,
        )
