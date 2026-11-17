"""
* @file     ${tests/pg/overlapping_project_groups_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the migration that lets a person hold several groups in one project.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the overlapping groups migration on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class OverlappingProjectGroupsMigrationBase(BloomTestCase):

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
        self.print_variables({"alembic": self.upgrade[1][-300:]})
        self.assertEqual(
            self.upgrade[0],
            0,
            msg=self.parameters.MSG_MIGRATION_HEAD,
            abort_on_fail=False,
        )

    def bud_upgrade_keeps_entries_policies_and_roles(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        kept = self.parameters.OVERLAP_KEPT
        self.print_variables({field: len(self.after[field]) for field in kept})
        self.assertEqual(
            {field: self.after[field] for field in kept},
            {field: self.state_before[field] for field in kept},
            msg=self.parameters.MSG_OVERLAP_KEPT,
            abort_on_fail=False,
        )

    def bud_second_group_for_a_person_is_stored(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"entry": self.overlap.entry})
        self.assertTrue(
            self.overlap.entry, msg=self.parameters.MSG_OVERLAP_STORED, abort_on_fail=False
        )

    def bud_same_group_a_second_time_is_refused(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.overlap.duplicate_refused,
            True,
            msg=self.parameters.MSG_OVERLAP_DUPLICATE,
            abort_on_fail=False,
        )

    def bud_second_entry_without_a_group_is_refused(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.overlap.plain_refused,
            True,
            msg=self.parameters.MSG_OVERLAP_PLAIN,
            abort_on_fail=False,
        )

    def bud_downgrade_over_an_overlap_is_refused_and_changes_nothing(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        overlapping = self.bloom.bloom_snapshot_project_access()
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.OVERLAP_BEFORE)
        after_refusal = self.bloom.bloom_snapshot_project_access()
        self.print_variables({"alembic": output[-300:], "revision": after_refusal["revision"]})
        self.assertNotEqual(code, 0, msg=self.parameters.MSG_OVERLAP_REFUSED, abort_on_fail=False)
        self.assertIn(
            self.parameters.OVERLAP_REFUSAL,
            output.lower(),
            msg=self.parameters.MSG_OVERLAP_REFUSAL_TEXT,
            abort_on_fail=False,
        )
        self.assertEqual(
            after_refusal,
            overlapping,
            msg=self.parameters.MSG_OVERLAP_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_downgrade_without_the_overlap_reaches_the_revision_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.bloom.bloom_delete_access_entry(self.overlap.entry)
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.OVERLAP_BEFORE)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(code, 0, msg=self.parameters.MSG_MIGRATION_DOWNGRADE, abort_on_fail=False)

    def bud_downgrade_restores_the_state_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        downgraded = self.bloom.bloom_snapshot_project_access()
        self.print_variables({"revision": downgraded["revision"]})
        self.assertEqual(
            downgraded,
            self.state_before,
            msg=self.parameters.MSG_OVERLAP_DOWNGRADED,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head_a_second_time(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(code, 0, msg=self.parameters.MSG_MIGRATION_HEAD_AGAIN, abort_on_fail=False)

    def bud_second_upgrade_restores_the_state_after(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        again = self.bloom.bloom_snapshot_project_access()
        self.print_variables({"revision": again["revision"]})
        self.assertEqual(
            again, self.after, msg=self.parameters.MSG_OVERLAP_UPGRADED_AGAIN, abort_on_fail=False
        )
