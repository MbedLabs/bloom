"""
* @file     ${tests/pg/pre_baseline_repair.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the repair of a schema created before the locked baseline.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the pre-baseline repair on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class PreBaselineRepairBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_migrations_reach_head(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.upgrade[1][-300:]})
        self.assertEqual(
            self.upgrade[0],
            0,
            msg=self.parameters.MSG_REPAIR_UPGRADE,
            abort_on_fail=False,
        )

    def bud_repair_runs_a_second_time_without_error(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"second run": self.repair.repeat_error})
        self.assertEqual(
            self.repair.repeat_error,
            None,
            msg=self.parameters.MSG_REPAIR_REPEAT,
            abort_on_fail=False,
        )

    def bud_repair_restores_the_account_email_column(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"columns named account_email": self.repair.column})
        self.assertEqual(
            self.repair.column,
            self.parameters.REPAIR_COLUMN_COUNT,
            msg=self.parameters.MSG_REPAIR_COLUMN,
            abort_on_fail=False,
        )

    def bud_repair_restores_the_sync_events_table(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"columns of the table": self.repair.table_columns})
        self.assertEqual(
            self.repair.table_columns,
            self.parameters.REPAIR_TABLE_COLUMNS,
            msg=self.parameters.MSG_REPAIR_TABLE,
            abort_on_fail=False,
        )

    def bud_repair_restores_the_index(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"indexes": self.repair.index})
        self.assertEqual(
            self.repair.index,
            self.parameters.REPAIR_INDEX_COUNT,
            msg=self.parameters.MSG_REPAIR_INDEX,
            abort_on_fail=False,
        )
