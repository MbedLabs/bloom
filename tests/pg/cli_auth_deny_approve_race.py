"""
* @file     ${tests/pg/cli_auth_deny_approve_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests denials and approvals of one CLI request sent at once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the deny and approve race on PostgreSQL.
"""

from tests.bloom_test_base import BloomTestCase


class CliAuthDenyApproveRaceBase(BloomTestCase):

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

    def bud_request_ends_once(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        statuses = [answer.status_code for answer in self.tc_answers]
        self.print_variables({"order": self.parameters.CLI_DENY_APPROVE_ORDER, "answers": statuses})
        self.assertEqual(
            statuses.count(self.parameters.STATUS_OK),
            1,
            msg=self.parameters.MSG_ENDED_ONCE,
            abort_on_fail=False,
        )
        self.assertTrue(
            set(statuses) <= set(self.parameters.CLI_CONSENT_ANSWERS),
            msg=self.parameters.MSG_END_LOSERS,
            abort_on_fail=False,
        )

    def bud_ended_request_is_not_found(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"lookup": self.tc_lookup.status_code})
        self.assertEqual(
            self.tc_lookup.status_code,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_ENDED_NOT_PENDING,
            abort_on_fail=False,
        )

    def bud_exchange_follows_the_winner(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"winner": self.tc_winner, "exchange": self.tc_exchanged.status_code})
        if self.tc_winner == self.parameters.CLI_DENY:
            self.assertEqual(
                self.tc_winning_answer.json(),
                {},
                msg=self.parameters.MSG_DENIED_EMPTY,
                abort_on_fail=False,
            )
            self.assertEqual(
                self.tc_exchanged.status_code,
                self.parameters.STATUS_BAD_REQUEST,
                msg=self.parameters.MSG_DENIED_NO_EXCHANGE,
                abort_on_fail=False,
            )
            return
        self.assertEqual(
            self.tc_exchanged.status_code,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_APPROVED_EXCHANGES,
            abort_on_fail=False,
        )
