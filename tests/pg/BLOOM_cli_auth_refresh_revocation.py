"""
* @file     ${tests/pg/BLOOM_cli_auth_refresh_revocation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A CLI refresh waits for an account revocation and is then refused.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a refresh sent while the account row is held, on migrated PostgreSQL.
"""

from tests.pg.cli_auth_refresh_revocation import CliAuthRefreshRevocationBase


class CliAuthRefreshRevocationTest(CliAuthRefreshRevocationBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        self.tc_upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.tc_outcome = self.bloom.bloom_refresh_during_revocation(
            self.parameters.CLI_REVOCATION_EMAIL, self.parameters.CLI_REFRESH_TOKEN
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CliAuthRefreshRevocationTest().run()
