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
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"start": self.tc_started.status_code})
        self.assertEqual(
            self.tc_started.status_code,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_CLI_STARTED,
            abort_on_fail=True,
        )

    def bud_approvals_succeed_once(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        statuses = [answer.status_code for answer in self.tc_approved]
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
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        statuses = [answer.status_code for answer in self.tc_exchanged]
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
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        statuses = [answer.status_code for answer in self.tc_refreshed]
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
