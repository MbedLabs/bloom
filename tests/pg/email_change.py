"""
* @file     ${tests/pg/email_change.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the change of an account's email and the verification an invitation gives.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the email change on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class EmailChangeBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_administrators_own_request_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_self_request.status, "body": self.tc_self_request.body}
        )
        self.assertEqual(
            self.tc_self_request.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_REQUEST,
            abort_on_fail=False,
        )

    def bud_administrator_is_told_to_confirm_from_the_current_email(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertIn(
            self.parameters.EMAIL_CURRENT_PHRASE,
            self.tc_self_request.body["message"].lower(),
            msg=self.parameters.MSG_EMAIL_SELF_PHRASE,
            abort_on_fail=False,
        )

    def bud_own_change_waits_for_the_current_mailbox(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"account": self.tc_self_pending.body})
        self.assertEqual(
            (
                self.tc_self_pending.body["email"],
                self.tc_self_pending.body["pending_email"],
                self.tc_self_pending.body["email_change_status"],
            ),
            (
                self.parameters.EMAIL_SELF_OLD,
                self.parameters.EMAIL_SELF_NEW,
                self.parameters.EMAIL_AWAITING_CURRENT,
            ),
            msg=self.parameters.MSG_EMAIL_SELF_PENDING,
            abort_on_fail=False,
        )

    def bud_own_change_mails_only_the_current_address(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            [
                (mail[self.parameters.EMAIL_SENDER_KEY], mail[self.parameters.EMAIL_TO_KEY])
                for mail in self.tc_self_request.mails
            ],
            [(self.parameters.EMAIL_AUTHORIZATION_SENDER, self.parameters.EMAIL_SELF_OLD)],
            msg=self.parameters.MSG_EMAIL_SELF_MAIL,
            abort_on_fail=False,
        )

    def bud_confirmation_from_the_current_mailbox_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_self_authorized.status, "body": self.tc_self_authorized.body}
        )
        self.assertEqual(
            self.tc_self_authorized.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_AUTHORIZED,
            abort_on_fail=False,
        )

    def bud_administrator_is_told_to_confirm_from_the_new_email(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertIn(
            self.parameters.EMAIL_NEW_PHRASE,
            self.tc_self_authorized.body["message"].lower(),
            msg=self.parameters.MSG_EMAIL_NEW_PHRASE,
            abort_on_fail=False,
        )

    def bud_own_change_then_waits_for_the_new_mailbox(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            (
                self.tc_self_waiting.status,
                self.tc_self_waiting.body["email"],
                self.tc_self_waiting.body["email_change_status"],
            ),
            (
                self.parameters.STATUS_OK,
                self.parameters.EMAIL_SELF_OLD,
                self.parameters.EMAIL_AWAITING,
            ),
            msg=self.parameters.MSG_EMAIL_SELF_WAITING,
            abort_on_fail=False,
        )

    def bud_new_address_is_mailed_after_the_current_mailbox_confirmed(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            [
                (mail[self.parameters.EMAIL_SENDER_KEY], mail[self.parameters.EMAIL_TO_KEY])
                for mail in self.tc_self_authorized.mails
            ],
            [(self.parameters.EMAIL_CHANGE_SENDER, self.parameters.EMAIL_SELF_NEW)],
            msg=self.parameters.MSG_EMAIL_NEW_MAIL,
            abort_on_fail=False,
        )

    def bud_confirmation_from_the_new_mailbox_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_self_confirmed.status, "body": self.tc_self_confirmed.body}
        )
        self.assertEqual(
            self.tc_self_confirmed.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_CONFIRMED,
            abort_on_fail=False,
        )

    def bud_own_change_ends_the_sessions_and_moves_the_sign_in(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"old token, old cookie, old email, new email": self.tc_self_after})
        self.assertEqual(
            self.tc_self_after,
            self.parameters.EMAIL_MOVED,
            msg=self.parameters.MSG_EMAIL_MOVED,
            abort_on_fail=False,
        )

    def bud_members_request_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_member_request.status, "body": self.tc_member_request.body}
        )
        self.assertEqual(
            self.tc_member_request.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_REQUEST,
            abort_on_fail=False,
        )

    def bud_members_request_sends_no_mail(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_member_request.mails,
            [],
            msg=self.parameters.MSG_EMAIL_NO_MAIL,
            abort_on_fail=False,
        )

    def bud_members_change_waits_as_requested(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_member_pending.body["email_change_status"],
            self.parameters.EMAIL_REQUESTED,
            msg=self.parameters.MSG_EMAIL_REQUESTED,
            abort_on_fail=False,
        )

    def bud_administrators_approval_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_member_approved.status, "body": self.tc_member_approved.body}
        )
        self.assertEqual(
            self.tc_member_approved.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_APPROVED,
            abort_on_fail=False,
        )

    def bud_approval_mail_names_the_old_and_the_new_address(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            [
                (mail[self.parameters.EMAIL_SENDER_KEY], mail["old_email"], mail["new_email"])
                for mail in self.tc_member_approved.mails
            ],
            [
                (
                    self.parameters.EMAIL_CHANGE_SENDER,
                    self.parameters.EMAIL_MEMBER_OLD,
                    self.parameters.EMAIL_MEMBER_NEW,
                )
            ],
            msg=self.parameters.MSG_EMAIL_APPROVAL_MAIL,
            abort_on_fail=False,
        )

    def bud_approved_change_keeps_the_email_until_confirmed(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            (
                self.tc_member_waiting.status,
                self.tc_member_waiting.body["email"],
                self.tc_member_waiting.body["pending_email"],
                self.tc_member_waiting.body["email_change_status"],
            ),
            (
                self.parameters.STATUS_OK,
                self.parameters.EMAIL_MEMBER_OLD,
                self.parameters.EMAIL_MEMBER_NEW,
                self.parameters.EMAIL_AWAITING,
            ),
            msg=self.parameters.MSG_EMAIL_AWAITING,
            abort_on_fail=False,
        )

    def bud_new_email_does_not_sign_in_before_the_confirmation(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"new email, old email": self.tc_member_not_yet})
        self.assertEqual(
            self.tc_member_not_yet,
            (self.parameters.STATUS_UNAUTHORIZED, self.parameters.STATUS_OK),
            msg=self.parameters.MSG_EMAIL_NOT_YET,
            abort_on_fail=False,
        )

    def bud_members_confirmation_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_member_confirmed.status, "body": self.tc_member_confirmed.body}
        )
        self.assertEqual(
            self.tc_member_confirmed.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_CONFIRMED,
            abort_on_fail=False,
        )

    def bud_members_change_ends_the_sessions_and_moves_the_sign_in(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"old token, old cookie, old email, new email": self.tc_member_after})
        self.assertEqual(
            self.tc_member_after,
            self.parameters.EMAIL_MOVED,
            msg=self.parameters.MSG_EMAIL_MOVED,
            abort_on_fail=False,
        )

    def bud_confirmed_account_has_the_new_email_and_no_pending_change(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"account": self.tc_member_account.body})
        self.assertEqual(
            (
                self.tc_member_account.body["email"],
                self.tc_member_account.body["pending_email"],
                self.tc_member_account.body["email_change_status"],
            ),
            (self.parameters.EMAIL_MEMBER_NEW, None, None),
            msg=self.parameters.MSG_EMAIL_AFTER,
            abort_on_fail=False,
        )

    def bud_confirmed_address_is_recorded_as_verified(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.tc_member_account.body["email_verified_at"],
            msg=self.parameters.MSG_EMAIL_VERIFIED,
            abort_on_fail=False,
        )

    def bud_token_for_another_pending_address_is_refused_400(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_stale_confirmed.status, "body": self.tc_stale_confirmed.body}
        )
        self.assertEqual(
            self.tc_stale_confirmed.status,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_EMAIL_STALE,
            abort_on_fail=False,
        )

    def bud_after_the_refused_token_only_the_old_email_signs_in(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"old, approved, other": self.tc_stale_logins})
        self.assertEqual(
            self.tc_stale_logins,
            (
                self.parameters.STATUS_OK,
                self.parameters.STATUS_UNAUTHORIZED,
                self.parameters.STATUS_UNAUTHORIZED,
            ),
            msg=self.parameters.MSG_EMAIL_STALE_LOGINS,
            abort_on_fail=False,
        )

    def bud_wrong_current_password_is_refused_400(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_guard_request.status, "body": self.tc_guard_request.body}
        )
        self.assertEqual(
            self.tc_guard_request.status,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_EMAIL_WRONG_PASSWORD,
            abort_on_fail=False,
        )

    def bud_refused_request_leaves_no_pending_email(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_guard_account.body["pending_email"],
            None,
            msg=self.parameters.MSG_EMAIL_NOT_STARTED,
            abort_on_fail=False,
        )

    def bud_general_account_update_refuses_an_email_422(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_admin_bypass.status, "body": self.tc_admin_bypass.body}
        )
        self.assertEqual(
            self.tc_admin_bypass.status,
            self.parameters.STATUS_UNPROCESSABLE,
            msg=self.parameters.MSG_EMAIL_BYPASS,
            abort_on_fail=False,
        )

    def bud_administrators_change_for_a_member_waits_for_confirmation(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_admin_started.status, "body": self.tc_admin_started.body}
        )
        self.assertEqual(
            (
                self.tc_admin_started.status,
                self.tc_admin_started.body["email"],
                self.tc_admin_started.body["email_change_status"],
            ),
            (
                self.parameters.STATUS_OK,
                self.parameters.EMAIL_ADMIN_OLD,
                self.parameters.EMAIL_AWAITING,
            ),
            msg=self.parameters.MSG_EMAIL_ADMIN_STARTED,
            abort_on_fail=False,
        )

    def bud_confirmation_of_the_administrators_change_is_answered_200(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_admin_confirmed.status, "body": self.tc_admin_confirmed.body}
        )
        self.assertEqual(
            self.tc_admin_confirmed.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_CONFIRMED,
            abort_on_fail=False,
        )

    def bud_administrators_change_moves_the_sign_in(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"old email, new email": self.tc_admin_logins})
        self.assertEqual(
            self.tc_admin_logins,
            (self.parameters.STATUS_UNAUTHORIZED, self.parameters.STATUS_OK),
            msg=self.parameters.MSG_EMAIL_ADMIN_MOVED,
            abort_on_fail=False,
        )

    def bud_accepted_invitation_asks_for_no_verification(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"status": self.tc_invite_accepted.status, "body": self.tc_invite_accepted.body}
        )
        self.assertEqual(
            (
                self.tc_invite_accepted.status,
                self.tc_invite_accepted.body["requires_email_verification"],
            ),
            (self.parameters.STATUS_OK, False),
            msg=self.parameters.MSG_EMAIL_INVITED,
            abort_on_fail=False,
        )

    def bud_invited_account_signs_in(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_invite_login,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EMAIL_INVITED_SIGN_IN,
            abort_on_fail=False,
        )

    def bud_invited_address_is_recorded_as_verified(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.tc_invite_account.body["email_verified_at"],
            msg=self.parameters.MSG_EMAIL_INVITED_VERIFIED,
            abort_on_fail=False,
        )
