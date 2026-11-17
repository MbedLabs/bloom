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
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        self.bloom.bloom_start_cli_api()
        self.headers = self.bloom.bloom_sign_in(self.parameters.CLI_ADMIN_EMAIL)
        self.started = self.bloom.bloom_start_cli_code_session(self.parameters.CLI_STATE)
        self.session_id = self.started.json().get("session_id", "")

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthConcurrentApprovalTest().run()
