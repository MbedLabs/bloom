"""
* @file     ${tests/pg/cli_auth_concurrent_approval.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests concurrent approvals, exchanges and refreshes of one CLI sign-in.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the concurrent CLI steps on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class CliAuthConcurrentApprovalBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_request_starts(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"start": self.started.status_code})
        self.assertEqual(
            self.started.status_code,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_CLI_STARTED,
            abort_on_fail=True,
        )

    def bud_approvals_succeed_once(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        approve = self.bloom.bloom_cli_approve_body(self.session_id)
        approved = self.bloom.bloom_race_cli(
            [(self.parameters.CLI_APPROVE, approve, self.headers)] * self.parameters.CLI_RACE_COPIES
        )
        self.code = next(
            (
                answer.json()["exchange_code"]
                for answer in approved
                if answer.status_code == self.parameters.STATUS_OK
            ),
            self.parameters.CLI_DENIED_CODE,
        )
        statuses = [answer.status_code for answer in approved]
        self.print_variables({"approvals": statuses})
        self.assertEqual(
            statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_APPROVED_ONCE,
            abort_on_fail=False,
        )
        self.assertTrue(
            set(statuses) <= set(self.parameters.CLI_CONSENT_ANSWERS),
            msg=self.parameters.MSG_APPROVE_LOSERS,
            abort_on_fail=False,
        )

    def bud_exchanges_succeed_once(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        exchange = self.bloom.bloom_cli_exchange_body(self.session_id, self.code)
        exchanged = self.bloom.bloom_race_cli(
            [(self.parameters.CLI_EXCHANGE, exchange, None)] * self.parameters.CLI_RACE_COPIES
        )
        self.refresh_token = next(
            (
                answer.json()["refresh_token"]
                for answer in exchanged
                if answer.status_code == self.parameters.STATUS_OK
            ),
            self.parameters.CLI_REFRESH_TOKEN,
        )
        statuses = [answer.status_code for answer in exchanged]
        self.print_variables({"exchanges": statuses})
        self.assertEqual(
            statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_EXCHANGED_ONCE,
            abort_on_fail=False,
        )
        self.assertTrue(
            set(statuses) <= set(self.parameters.CLI_CONSENT_ANSWERS),
            msg=self.parameters.MSG_EXCHANGE_LOSERS,
            abort_on_fail=False,
        )

    def bud_refreshes_succeed_once(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        refresh = {"refresh_token": self.refresh_token}
        refreshed = self.bloom.bloom_race_cli(
            [(self.parameters.CLI_REFRESH, refresh, None)] * self.parameters.CLI_RACE_COPIES
        )
        statuses = [answer.status_code for answer in refreshed]
        self.print_variables({"refreshes": statuses})
        self.assertEqual(
            statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_REFRESHED_ONCE,
            abort_on_fail=False,
        )
        self.assertTrue(
            set(statuses) <= set(self.parameters.CLI_REFRESH_ANSWERS),
            msg=self.parameters.MSG_REFRESH_LOSERS,
            abort_on_fail=False,
        )
