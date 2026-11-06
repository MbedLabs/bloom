"""
* @file     ${tests/pg/cli_auth_refresh_revocation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a CLI refresh that runs while the account is being revoked.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the refresh and revocation race on PostgreSQL.
"""

from tests.bloom_test_base import BloomTestCase


class CliAuthRefreshRevocationBase(BloomTestCase):

    def bud_database_upgrades(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.tc_upgrade
        if code:
            self.log_info(output)
        self.print_variables({"exit code": code})
        self.assertEqual(code, 0, msg=self.parameters.MSG_FRESH_UPGRADE, abort_on_fail=True)

    def bud_refresh_waits_for_the_account_lock(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"asked for the lock": self.tc_outcome.waited})
        self.assertTrue(
            self.tc_outcome.waited, msg=self.parameters.MSG_REFRESH_WAITED, abort_on_fail=False
        )

    def bud_refresh_is_refused_after_the_revocation(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"refusal": self.tc_outcome.reason})
        self.assertEqual(
            self.tc_outcome.reason,
            self.parameters.CLI_INVALID_TOKEN,
            msg=self.parameters.MSG_REFRESH_REVOKED,
            abort_on_fail=False,
        )
