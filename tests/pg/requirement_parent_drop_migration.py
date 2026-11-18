"""
* @file     ${tests/pg/requirement_parent_drop_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the migration that drops requirements.parent_id.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement parent migration on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class RequirementParentDropMigrationBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_migrations_reach_the_revision_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.before[1][-300:]})
        self.assertEqual(
            self.before[0],
            0,
            msg=self.parameters.MSG_MIGRATION_BEFORE,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(
            code,
            0,
            msg=self.parameters.MSG_MIGRATION_HEAD,
            abort_on_fail=False,
        )

    def bud_upgrade_drops_the_parent_and_keeps_the_requirements(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        upgraded = self.bloom.bloom_read_requirement_parent_state()
        self.print_variables({"requirements, parent_id exists": upgraded})
        self.assertEqual(
            upgraded,
            (self.parameters.PARENT_REQ_IDS, False),
            msg=self.parameters.MSG_PARENT_DROPPED,
            abort_on_fail=False,
        )

    def bud_downgrade_reaches_the_revision_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.PARENT_BEFORE)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(
            code,
            0,
            msg=self.parameters.MSG_MIGRATION_DOWNGRADE,
            abort_on_fail=False,
        )

    def bud_downgrade_restores_the_parent_and_keeps_the_requirements(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        downgraded = self.bloom.bloom_read_requirement_parent_state()
        self.print_variables({"requirements, parent_id exists": downgraded})
        self.assertEqual(
            downgraded,
            (self.parameters.PARENT_REQ_IDS, True),
            msg=self.parameters.MSG_PARENT_RESTORED,
            abort_on_fail=False,
        )
