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

    def bud_refresh_token_is_issued(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.tc_refresh_token,
            msg=self.parameters.MSG_TOKEN_RACE_ISSUED.format(
                token=self.parameters.TOKEN_RACE_USE["refresh"]
            ),
            abort_on_fail=False,
        )

    def bud_one_use_of_the_refresh_token_succeeds(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"statuses": self.tc_refresh_statuses})
        self.assertEqual(
            self.tc_refresh_statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_TOKEN_RACE_ONE.format(
                token=self.parameters.TOKEN_RACE_USE["refresh"]
            ),
            abort_on_fail=False,
        )

    def bud_every_other_use_of_the_refresh_token_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            sorted(set(self.tc_refresh_statuses)),
            [self.parameters.STATUS_OK, self.parameters.STATUS_UNAUTHORIZED],
            msg=self.parameters.MSG_TOKEN_RACE_OTHERS.format(
                token=self.parameters.TOKEN_RACE_USE["refresh"],
                status=self.parameters.STATUS_UNAUTHORIZED,
            ),
            abort_on_fail=False,
        )

    def bud_reset_token_is_issued(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.tc_reset_token,
            msg=self.parameters.MSG_TOKEN_RACE_ISSUED.format(
                token=self.parameters.TOKEN_RACE_USE["reset"]
            ),
            abort_on_fail=False,
        )

    def bud_one_use_of_the_reset_token_succeeds(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"statuses": self.tc_reset_statuses})
        self.assertEqual(
            self.tc_reset_statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_TOKEN_RACE_ONE.format(
                token=self.parameters.TOKEN_RACE_USE["reset"]
            ),
            abort_on_fail=False,
        )

    def bud_every_other_use_of_the_reset_token_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            sorted(set(self.tc_reset_statuses)),
            [self.parameters.STATUS_OK, self.parameters.STATUS_BAD_REQUEST],
            msg=self.parameters.MSG_TOKEN_RACE_OTHERS.format(
                token=self.parameters.TOKEN_RACE_USE["reset"],
                status=self.parameters.STATUS_BAD_REQUEST,
            ),
            abort_on_fail=False,
        )

    def bud_invite_token_is_issued(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.tc_invite_token,
            msg=self.parameters.MSG_TOKEN_RACE_ISSUED.format(
                token=self.parameters.TOKEN_RACE_USE["invite"]
            ),
            abort_on_fail=False,
        )

    def bud_one_use_of_the_invite_token_succeeds(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"statuses": self.tc_invite_statuses})
        self.assertEqual(
            self.tc_invite_statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_TOKEN_RACE_ONE.format(
                token=self.parameters.TOKEN_RACE_USE["invite"]
            ),
            abort_on_fail=False,
        )

    def bud_every_other_use_of_the_invite_token_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            sorted(set(self.tc_invite_statuses)),
            [self.parameters.STATUS_OK, self.parameters.STATUS_BAD_REQUEST],
            msg=self.parameters.MSG_TOKEN_RACE_OTHERS.format(
                token=self.parameters.TOKEN_RACE_USE["invite"],
                status=self.parameters.STATUS_BAD_REQUEST,
            ),
            abort_on_fail=False,
        )

    def bud_verify_token_is_issued(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertTrue(
            self.tc_verify_token,
            msg=self.parameters.MSG_TOKEN_RACE_ISSUED.format(
                token=self.parameters.TOKEN_RACE_USE["verify"]
            ),
            abort_on_fail=False,
        )

    def bud_one_use_of_the_verify_token_succeeds(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"statuses": self.tc_verify_statuses})
        self.assertEqual(
            self.tc_verify_statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_TOKEN_RACE_ONE.format(
                token=self.parameters.TOKEN_RACE_USE["verify"]
            ),
            abort_on_fail=False,
        )

    def bud_every_other_use_of_the_verify_token_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            sorted(set(self.tc_verify_statuses)),
            [self.parameters.STATUS_OK, self.parameters.STATUS_BAD_REQUEST],
            msg=self.parameters.MSG_TOKEN_RACE_OTHERS.format(
                token=self.parameters.TOKEN_RACE_USE["verify"],
                status=self.parameters.STATUS_BAD_REQUEST,
            ),
            abort_on_fail=False,
        )
