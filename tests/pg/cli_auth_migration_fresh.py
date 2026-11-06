"""
* @file     ${tests/pg/cli_auth_migration_fresh.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the migrations on an empty PostgreSQL database.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the fresh database migration.
"""

from tests.bloom_test_base import BloomTestCase


class CliAuthMigrationFreshBase(BloomTestCase):

    def bud_fresh_database_upgrades(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.tc_upgrade
        if code:
            self.log_info(output)
        self.print_variables({"exit code": code})
        self.assertEqual(code, 0, msg=self.parameters.MSG_FRESH_UPGRADE, abort_on_fail=True)

    def bud_migrations_have_one_head(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"heads": self.tc_heads})
        self.assertEqual(
            len(self.tc_heads), 1, msg=self.parameters.MSG_SINGLE_HEAD, abort_on_fail=False
        )

    def bud_database_is_at_the_head(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"revision": self.tc_revision, "heads": self.tc_heads})
        self.assertEqual(
            [self.tc_revision], self.tc_heads, msg=self.parameters.MSG_AT_HEAD, abort_on_fail=False
        )
