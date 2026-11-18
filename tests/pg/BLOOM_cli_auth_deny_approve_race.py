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
        self.headers = self.bloom.bloom_sign_in(self.parameters.CLI_ADMIN_EMAIL)
        self.started = self.bloom.bloom_start_cli_code_session(self.parameters.CLI_STATE)
        self.session_id = self.started.json().get("session_id", "")

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthDenyApproveRaceTest().run()
