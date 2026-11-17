"""
* @file     ${tests/pg/token_concurrency.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests one-time tokens used several times at once.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the token races on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class TokenConcurrencyBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_a_refresh_token_works_once_under_concurrent_use(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        token = self.bloom.bloom_log_in_for_cookie(values.ADMIN_EMAIL, values.API_PASSWORD).cookie
        statuses = self.bloom.bloom_race_requests("/api/auth/refresh", cookie=token)
        values = self.parameters
        name = values.TOKEN_RACE_USE["refresh"]
        self.print_variables({"statuses": statuses})
        self.assertTrue(
            token, msg=values.MSG_TOKEN_RACE_ISSUED.format(token=name), abort_on_fail=False
        )
        self.assertEqual(
            statuses.count(values.STATUS_OK),
            1,
            msg=values.MSG_TOKEN_RACE_ONE.format(token=name),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(set(statuses)),
            [values.STATUS_OK, values.STATUS_UNAUTHORIZED],
            msg=values.MSG_TOKEN_RACE_OTHERS.format(token=name, status=values.STATUS_UNAUTHORIZED),
            abort_on_fail=False,
        )

    def bud_a_reset_token_works_once_under_concurrent_use(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        email = values.TOKEN_RACE_RESET_EMAIL
        self.bloom.bloom_add_account(email, values.API_PASSWORD, values.SESSION_ROLE)
        token = self.bloom.bloom_request_password_reset(email).token
        body = {"token": token, "new_password": values.SESSION_NEW_PASSWORD}
        statuses = self.bloom.bloom_race_requests("/api/auth/reset-password", json=body)
        values = self.parameters
        name = values.TOKEN_RACE_USE["reset"]
        self.print_variables({"statuses": statuses})
        self.assertTrue(
            token, msg=values.MSG_TOKEN_RACE_ISSUED.format(token=name), abort_on_fail=False
        )
        self.assertEqual(
            statuses.count(values.STATUS_OK),
            1,
            msg=values.MSG_TOKEN_RACE_ONE.format(token=name),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(set(statuses)),
            [values.STATUS_OK, values.STATUS_BAD_REQUEST],
            msg=values.MSG_TOKEN_RACE_OTHERS.format(token=name, status=values.STATUS_BAD_REQUEST),
            abort_on_fail=False,
        )

    def bud_an_invite_token_works_once_under_concurrent_use(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        admin = self.bloom.bloom_log_in_for_cookie(values.ADMIN_EMAIL, values.API_PASSWORD)
        token = self.bloom.bloom_invite(
            admin.access_token, values.TOKEN_RACE_INVITE_EMAIL, values.SESSION_ROLE
        ).token
        body = {"token": token, "password": values.SESSION_NEW_PASSWORD}
        statuses = self.bloom.bloom_race_requests("/api/auth/accept-invite", json=body)
        values = self.parameters
        name = values.TOKEN_RACE_USE["invite"]
        self.print_variables({"statuses": statuses})
        self.assertTrue(
            token, msg=values.MSG_TOKEN_RACE_ISSUED.format(token=name), abort_on_fail=False
        )
        self.assertEqual(
            statuses.count(values.STATUS_OK),
            1,
            msg=values.MSG_TOKEN_RACE_ONE.format(token=name),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(set(statuses)),
            [values.STATUS_OK, values.STATUS_BAD_REQUEST],
            msg=values.MSG_TOKEN_RACE_OTHERS.format(token=name, status=values.STATUS_BAD_REQUEST),
            abort_on_fail=False,
        )

    def bud_a_verification_token_works_once_under_concurrent_use(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        email = values.TOKEN_RACE_VERIFY_EMAIL
        self.bloom.bloom_add_account(email, values.API_PASSWORD, values.SESSION_ROLE)
        member = self.bloom.bloom_log_in_for_cookie(email, values.API_PASSWORD)
        token = self.bloom.bloom_request_verification(member.access_token).token
        statuses = self.bloom.bloom_race_requests("/api/auth/verify-email", json={"token": token})
        values = self.parameters
        name = values.TOKEN_RACE_USE["verify"]
        self.print_variables({"statuses": statuses})
        self.assertTrue(
            token, msg=values.MSG_TOKEN_RACE_ISSUED.format(token=name), abort_on_fail=False
        )
        self.assertEqual(
            statuses.count(values.STATUS_OK),
            1,
            msg=values.MSG_TOKEN_RACE_ONE.format(token=name),
            abort_on_fail=False,
        )
        self.assertEqual(
            sorted(set(statuses)),
            [values.STATUS_OK, values.STATUS_BAD_REQUEST],
            msg=values.MSG_TOKEN_RACE_OTHERS.format(token=name, status=values.STATUS_BAD_REQUEST),
            abort_on_fail=False,
        )
