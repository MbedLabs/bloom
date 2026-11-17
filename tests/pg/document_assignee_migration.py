"""
* @file     ${tests/pg/document_assignee_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the migration that gives each existing workflow an assignee.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the assignee migration on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class DocumentAssigneeMigrationBase(BloomTestCase):

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

    def bud_existing_workflow_is_assigned_to_its_revision_creator(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        assignees = self.bloom.bloom_read_workflow_assignees()
        self.print_variables({"creator": self.person, "creator and assignee": assignees})
        self.assertEqual(
            assignees,
            [(self.person, self.person)],
            msg=self.parameters.MSG_ASSIGNEE_IS_CREATOR,
            abort_on_fail=False,
        )

    def bud_downgrade_reaches_the_revision_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.ASSIGNEE_BEFORE)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(
            code,
            0,
            msg=self.parameters.MSG_MIGRATION_DOWNGRADE,
            abort_on_fail=False,
        )
