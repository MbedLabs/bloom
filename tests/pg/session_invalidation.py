"""
* @file     ${tests/pg/session_invalidation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the sessions of an account after its password changes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the session invalidation on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class SessionInvalidationBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_session_reads_the_account_before_the_change(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.change_before})
        self.assertEqual(
            self.change_before,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_BEFORE.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_password_change_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.change})
        self.assertEqual(
            self.change,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_DONE.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_access_token_from_before_the_change_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.change_after.account})
        self.assertEqual(
            self.change_after.account,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_ACCESS.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_refresh_cookie_from_before_the_change_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.change_after.refresh})
        self.assertEqual(
            self.change_after.refresh,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_REFRESH.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_old_password_is_refused_after_the_change(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.change_after.old_password})
        self.assertEqual(
            self.change_after.old_password,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_OLD_PASSWORD.format(
                event=self.parameters.SESSION_CHANGE
            ),
            abort_on_fail=False,
        )

    def bud_new_password_signs_in_after_the_change(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.change_after.new_password})
        self.assertEqual(
            self.change_after.new_password,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_NEW_PASSWORD.format(
                event=self.parameters.SESSION_CHANGE
            ),
            abort_on_fail=False,
        )

    def bud_session_reads_the_account_before_the_reset(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.reset_before})
        self.assertEqual(
            self.reset_before,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_BEFORE.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_reset_mail_carries_a_token(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.reset_mail.token, msg=self.parameters.MSG_SESSION_MAIL, abort_on_fail=False
        )

    def bud_password_reset_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.reset})
        self.assertEqual(
            self.reset,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_DONE.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_access_token_from_before_the_reset_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.reset_after.account})
        self.assertEqual(
            self.reset_after.account,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_ACCESS.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_refresh_cookie_from_before_the_reset_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.reset_after.refresh})
        self.assertEqual(
            self.reset_after.refresh,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_REFRESH.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_old_password_is_refused_after_the_reset(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.reset_after.old_password})
        self.assertEqual(
            self.reset_after.old_password,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_OLD_PASSWORD.format(
                event=self.parameters.SESSION_RESET
            ),
            abort_on_fail=False,
        )

    def bud_new_password_signs_in_after_the_reset(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.reset_after.new_password})
        self.assertEqual(
            self.reset_after.new_password,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_NEW_PASSWORD.format(
                event=self.parameters.SESSION_RESET
            ),
            abort_on_fail=False,
        )
