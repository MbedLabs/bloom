"""
* @file     ${tests/pg/BLOOM_cli_auth_concurrent_approval.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Concurrent approvals, exchanges and refreshes of one CLI sign-in each succeed once.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests copies of each CLI step sent at once on a new PostgreSQL database.
"""

from tests.pg.cli_auth_concurrent_approval import CliAuthConcurrentApprovalBase


class CliAuthConcurrentApprovalTest(CliAuthConcurrentApprovalBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres()
        if not self.tc_postgres:
            return
        self.bloom.bloom_start_cli_api()
        headers = self.bloom.bloom_sign_in(self.parameters.CLI_ADMIN_EMAIL)
        copies = self.parameters.CLI_RACE_COPIES
        self.tc_started = self.bloom.bloom_start_cli_code_session(self.parameters.CLI_STATE)
        session_id = self.tc_started.json().get("session_id", "")

        approve = self.bloom.bloom_cli_approve_body(session_id)
        self.tc_approved = self.bloom.bloom_race_cli(
            [(self.parameters.CLI_APPROVE, approve, headers)] * copies
        )
        code = next(
            (
                answer.json()["exchange_code"]
                for answer in self.tc_approved
                if answer.status_code == self.parameters.STATUS_OK
            ),
            self.parameters.CLI_DENIED_CODE,
        )

        exchange = self.bloom.bloom_cli_exchange_body(session_id, code)
        self.tc_exchanged = self.bloom.bloom_race_cli(
            [(self.parameters.CLI_EXCHANGE, exchange, None)] * copies
        )
        refresh_token = next(
            (
                answer.json()["refresh_token"]
                for answer in self.tc_exchanged
                if answer.status_code == self.parameters.STATUS_OK
            ),
            self.parameters.CLI_REFRESH_TOKEN,
        )

        refresh = {"refresh_token": refresh_token}
        self.tc_refreshed = self.bloom.bloom_race_cli(
            [(self.parameters.CLI_REFRESH, refresh, None)] * copies
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthConcurrentApprovalTest().run()
