"""
* @file     ${tests/pg/cli_auth_deny_approve_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests denials and approvals of one CLI request sent at once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the deny and approve race on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class CliAuthDenyApproveRaceBase(BloomTestCase):

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

    def bud_request_ends_once(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        bodies = {
            self.parameters.CLI_DENY: {"session_id": self.session_id},
            self.parameters.CLI_APPROVE: self.bloom.bloom_cli_approve_body(self.session_id),
        }
        paths = list(self.parameters.CLI_DENY_APPROVE_ORDER)
        answers = self.bloom.bloom_race_cli([(path, bodies[path], self.headers) for path in paths])
        self.winner, self.winning_answer = next(
            (
                (path, answer)
                for path, answer in zip(paths, answers)
                if answer.status_code == self.parameters.STATUS_OK
            ),
            (None, None),
        )
        statuses = [answer.status_code for answer in answers]
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
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        lookup = self.bloom.bloom_get_cli_session(self.session_id, self.headers)
        self.print_variables({"lookup": lookup.status_code})
        self.assertEqual(
            lookup.status_code,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_ENDED_NOT_PENDING,
            abort_on_fail=False,
        )

    def bud_exchange_follows_the_winner(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code = self.parameters.CLI_DENIED_CODE
        if self.winner == self.parameters.CLI_APPROVE:
            code = self.winning_answer.json()["exchange_code"]
        exchanged = self.bloom.bloom_cli_exchange(self.session_id, code)
        self.print_variables({"winner": self.winner, "exchange": exchanged.status_code})
        if self.winner == self.parameters.CLI_DENY:
            self.assertEqual(
                self.winning_answer.json(),
                {},
                msg=self.parameters.MSG_DENIED_EMPTY,
                abort_on_fail=False,
            )
            self.assertEqual(
                exchanged.status_code,
                self.parameters.STATUS_BAD_REQUEST,
                msg=self.parameters.MSG_DENIED_NO_EXCHANGE,
                abort_on_fail=False,
            )
            return
        self.assertEqual(
            exchanged.status_code,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_APPROVED_EXCHANGES,
            abort_on_fail=False,
        )
