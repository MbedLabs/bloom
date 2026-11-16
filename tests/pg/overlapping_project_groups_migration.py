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
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_before[1][-300:]})
        self.assertEqual(
            self.tc_before[0],
            0,
            msg=self.parameters.MSG_MIGRATION_BEFORE,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_upgrade[1][-300:]})
        self.assertEqual(
            self.tc_upgrade[0],
            0,
            msg=self.parameters.MSG_MIGRATION_HEAD,
            abort_on_fail=False,
        )

    def bud_upgrade_keeps_entries_policies_and_roles(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        kept = self.parameters.OVERLAP_KEPT
        self.print_variables({field: len(self.tc_after[field]) for field in kept})
        self.assertEqual(
            {field: self.tc_after[field] for field in kept},
            {field: self.tc_state_before[field] for field in kept},
            msg=self.parameters.MSG_OVERLAP_KEPT,
            abort_on_fail=False,
        )

    def bud_second_group_for_a_person_is_stored(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"entry": self.tc_overlap.entry})
        self.assertTrue(
            self.tc_overlap.entry, msg=self.parameters.MSG_OVERLAP_STORED, abort_on_fail=False
        )

    def bud_same_group_a_second_time_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_overlap.duplicate_refused,
            True,
            msg=self.parameters.MSG_OVERLAP_DUPLICATE,
            abort_on_fail=False,
        )

    def bud_second_entry_without_a_group_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_overlap.plain_refused,
            True,
            msg=self.parameters.MSG_OVERLAP_PLAIN,
            abort_on_fail=False,
        )

    def bud_downgrade_over_an_overlap_is_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_refused[1][-300:]})
        self.assertNotEqual(
            self.tc_refused[0],
            0,
            msg=self.parameters.MSG_OVERLAP_REFUSED,
            abort_on_fail=False,
        )

    def bud_refusal_names_the_overlapping_groups(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertIn(
            self.parameters.OVERLAP_REFUSAL,
            self.tc_refused[1].lower(),
            msg=self.parameters.MSG_OVERLAP_REFUSAL_TEXT,
            abort_on_fail=False,
        )

    def bud_refused_downgrade_changes_nothing(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"revision": self.tc_after_refusal["revision"]})
        self.assertEqual(
            self.tc_after_refusal,
            self.tc_overlapping,
            msg=self.parameters.MSG_OVERLAP_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_downgrade_without_the_overlap_reaches_the_revision_before(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_downgrade[1][-300:]})
        self.assertEqual(
            self.tc_downgrade[0],
            0,
            msg=self.parameters.MSG_MIGRATION_DOWNGRADE,
            abort_on_fail=False,
        )

    def bud_downgrade_restores_the_state_before(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"revision": self.tc_downgraded["revision"]})
        self.assertEqual(
            self.tc_downgraded,
            self.tc_state_before,
            msg=self.parameters.MSG_OVERLAP_DOWNGRADED,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head_a_second_time(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_upgrade_again[1][-300:]})
        self.assertEqual(
            self.tc_upgrade_again[0],
            0,
            msg=self.parameters.MSG_MIGRATION_HEAD_AGAIN,
            abort_on_fail=False,
        )

    def bud_second_upgrade_restores_the_state_after(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"revision": self.tc_upgraded_again["revision"]})
        self.assertEqual(
            self.tc_upgraded_again,
            self.tc_after,
            msg=self.parameters.MSG_OVERLAP_UPGRADED_AGAIN,
            abort_on_fail=False,
        )
