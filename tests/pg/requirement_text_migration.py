"""
* @file     ${tests/pg/requirement_text_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the migration of requirement editor text into descriptions on PostgreSQL.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement text migration.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class RequirementTextMigrationBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_every_alembic_command_succeeds(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for code, output in self.commands:
            if code:
                self.log_info(output)
        codes = [code for code, _ in self.commands]
        self.print_variables({"exit codes": codes})
        self.assertEqual(
            codes, [0] * len(codes), msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True
        )

    def bud_upgrade_moves_editor_text_into_descriptions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"upgraded": self.upgraded})
        self._equal(
            self.upgraded,
            self.parameters.TEXT_MIGRATION_EXPECTED,
            self.parameters.MSG_TEXT_MIGRATION_UPGRADE,
        )

    def bud_downgrade_keeps_the_descriptions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"downgraded": self.downgraded})
        self._equal(
            self.downgraded,
            (self.parameters.TEXT_MIGRATION_BEFORE, self.parameters.TEXT_MIGRATION_EXPECTED),
            self.parameters.MSG_TEXT_MIGRATION_DOWNGRADE,
        )

    def bud_upgrading_again_keeps_the_descriptions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"upgraded again": self.reupgraded})
        self._equal(
            self.reupgraded,
            (self.parameters.TEXT_MIGRATION_REVISION, self.parameters.TEXT_MIGRATION_EXPECTED),
            self.parameters.MSG_TEXT_MIGRATION_REUPGRADE,
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
