"""
* @file     ${tests/pg/BLOOM_cli_auth_deny_approve_race.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Denials and approvals of one CLI request sent at once end it once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests two denials and two approvals in a drawn order on new PostgreSQL.
"""

from tests.pg.cli_auth_deny_approve_race import CliAuthDenyApproveRaceBase


class CliAuthDenyApproveRaceTest(CliAuthDenyApproveRaceBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        self.bloom.bloom_start_cli_api()
        headers = self.bloom.bloom_sign_in(self.parameters.CLI_ADMIN_EMAIL)
        self.started = self.bloom.bloom_start_cli_code_session(self.parameters.CLI_STATE)
        session_id = self.started.json().get("session_id", "")

        bodies = {
            self.parameters.CLI_DENY: {"session_id": session_id},
            self.parameters.CLI_APPROVE: self.bloom.bloom_cli_approve_body(session_id),
        }
        paths = list(self.parameters.CLI_DENY_APPROVE_ORDER)
        self.answers = self.bloom.bloom_race_cli([(path, bodies[path], headers) for path in paths])
        self.winner, self.winning_answer = next(
            (
                (path, answer)
                for path, answer in zip(paths, self.answers)
                if answer.status_code == self.parameters.STATUS_OK
            ),
            (None, None),
        )
        self.lookup = self.bloom.bloom_get_cli_session(session_id, headers)
        code = self.parameters.CLI_DENIED_CODE
        if self.winner == self.parameters.CLI_APPROVE:
            code = self.winning_answer.json()["exchange_code"]
        self.exchanged = self.bloom.bloom_cli_exchange(session_id, code)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthDenyApproveRaceTest().run()
