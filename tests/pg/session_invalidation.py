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
        status = self.bloom.bloom_read_account(self.change_login.access_token).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_BEFORE.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_password_change_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        status = self.bloom.bloom_change_password(
            self.change_login.access_token, values.SESSION_OLD_PASSWORD, values.SESSION_NEW_PASSWORD
        )
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            values.STATUS_OK,
            msg=values.MSG_SESSION_DONE.format(event=values.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_access_token_from_before_the_change_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        status = self.bloom.bloom_read_account(self.change_login.access_token).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_ACCESS.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_refresh_cookie_from_before_the_change_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        status = self.bloom.bloom_refresh(self.change_login.cookie).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_REFRESH.format(event=self.parameters.SESSION_CHANGE),
            abort_on_fail=False,
        )

    def bud_old_password_is_refused_after_the_change(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        status = self.bloom.bloom_log_in_for_cookie(
            self.parameters.SESSION_CHANGE_EMAIL, self.parameters.SESSION_OLD_PASSWORD
        ).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
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
        status = self.bloom.bloom_log_in_for_cookie(
            self.parameters.SESSION_CHANGE_EMAIL, self.parameters.SESSION_NEW_PASSWORD
        ).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
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
        status = self.bloom.bloom_read_account(self.reset_login.access_token).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_BEFORE.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_a_reset_mail_carries_a_token_and_the_reset_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        mail = self.bloom.bloom_request_password_reset(values.SESSION_RESET_EMAIL)
        self.assertTrue(mail.token, msg=values.MSG_SESSION_MAIL, abort_on_fail=True)
        status = self.bloom.bloom_reset_password(mail.token, values.SESSION_NEW_PASSWORD)
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            values.STATUS_OK,
            msg=values.MSG_SESSION_DONE.format(event=values.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_access_token_from_before_the_reset_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        status = self.bloom.bloom_read_account(self.reset_login.access_token).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_ACCESS.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_refresh_cookie_from_before_the_reset_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        status = self.bloom.bloom_refresh(self.reset_login.cookie).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_SESSION_REFRESH.format(event=self.parameters.SESSION_RESET),
            abort_on_fail=False,
        )

    def bud_old_password_is_refused_after_the_reset(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        status = self.bloom.bloom_log_in_for_cookie(
            self.parameters.SESSION_RESET_EMAIL, self.parameters.SESSION_OLD_PASSWORD
        ).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
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
        status = self.bloom.bloom_log_in_for_cookie(
            self.parameters.SESSION_RESET_EMAIL, self.parameters.SESSION_NEW_PASSWORD
        ).status
        self.print_variables({"status": status})
        self.assertEqual(
            status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SESSION_NEW_PASSWORD.format(
                event=self.parameters.SESSION_RESET
            ),
            abort_on_fail=False,
        )
