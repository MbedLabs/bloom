"""
* @file     ${tests/pg/refresh_flow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the refresh cookie from sign-in to sign-out.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the refresh-token flow on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class RefreshFlowBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_sign_in_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.login.status})
        self.assertEqual(
            self.login.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_REFRESH_LOGIN,
            abort_on_fail=False,
        )

    def bud_sign_in_sets_the_refresh_cookie(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"set-cookie": self.login.set_cookie})
        self.assertTrue(
            self.login.cookie, msg=self.parameters.MSG_REFRESH_COOKIE_SET, abort_on_fail=False
        )

    def bud_refresh_cookie_is_http_only(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertIn(
            self.parameters.REFRESH_COOKIE_FLAG,
            self.login.set_cookie,
            msg=self.parameters.MSG_REFRESH_HTTP_ONLY,
            abort_on_fail=False,
        )

    def bud_refresh_cookie_is_limited_to_the_auth_path(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertIn(
            self.parameters.REFRESH_COOKIE_PATH,
            self.login.set_cookie,
            msg=self.parameters.MSG_REFRESH_PATH,
            abort_on_fail=False,
        )

    def bud_refresh_with_the_cookie_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.refresh.status, "body": self.refresh.body})
        self.assertEqual(
            self.refresh.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_REFRESH_OK,
            abort_on_fail=False,
        )

    def bud_refreshed_token_reads_the_account(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.account.status, "body": self.account.body})
        self.assertEqual(
            (self.account.status, self.account.body.get(self.parameters.REFRESH_EMAIL_KEY)),
            (self.parameters.STATUS_OK, self.parameters.ADMIN_EMAIL),
            msg=self.parameters.MSG_REFRESH_ACCOUNT,
            abort_on_fail=False,
        )

    def bud_refresh_without_the_cookie_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.without_cookie.status})
        self.assertEqual(
            self.without_cookie.status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_REFRESH_NO_COOKIE,
            abort_on_fail=False,
        )

    def bud_refresh_sets_a_new_cookie(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.refresh.cookie, msg=self.parameters.MSG_REFRESH_NEW_COOKIE, abort_on_fail=False
        )
        self.assertNotEqual(
            self.refresh.cookie,
            self.login.cookie,
            msg=self.parameters.MSG_REFRESH_ROTATED,
            abort_on_fail=False,
        )

    def bud_cookie_from_before_the_refresh_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.replay.status, "body": self.replay.body})
        self.assertEqual(
            self.replay.status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_REFRESH_REPLAY,
            abort_on_fail=False,
        )

    def bud_sign_out_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.logout.status})
        self.assertEqual(
            self.logout.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_REFRESH_LOGOUT,
            abort_on_fail=False,
        )

    def bud_cookie_of_a_signed_out_session_is_refused_401(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.after_logout.status})
        self.assertEqual(
            self.after_logout.status,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_REFRESH_AFTER_LOGOUT,
            abort_on_fail=False,
        )
