"""
* @file     ${tests/pg/campaign_public_id_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the campaign and suite public ID migration on PostgreSQL.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the public ID migration.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class CampaignPublicIdMigrationBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_the_database_starts_before_the_public_ids(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        if self.prepared[0]:
            self.log_info(self.prepared[1])
        self.assertEqual(
            self.prepared[0], 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True
        )

    def bud_missing_public_ids_get_the_next_free_number(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.PUBLIC_ID_REVISION)
        if code:
            self.log_info(output)
        self.assertEqual(code, 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True)
        public_ids = self.bloom.bloom_read_campaign_public_ids()
        for prefix, expected in self.parameters.CAMPAIGN_EXPECTED.items():
            found = [public_ids[row_id] for row_id in self.ids[prefix]]
            self.print_variables(
                {"seeded": self.parameters.CAMPAIGN_SEEDS[prefix], "public IDs": found}
            )
            self.assertEqual(
                found, expected, msg=self.parameters.MSG_PUBLIC_IDS_NUMBERED, abort_on_fail=False
            )

    def bud_public_ids_become_required_and_unique(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        shape = self.bloom.bloom_read_public_id_shape()
        self.print_variables({"shape": shape})
        self.assertEqual(
            shape,
            {
                "nullable": self.parameters.NOT_NULLABLE,
                "indexes": self.parameters.PUBLIC_ID_INDEXES,
                "revision": self.parameters.PUBLIC_ID_REVISION,
            },
            msg=self.parameters.MSG_PUBLIC_IDS_REQUIRED,
            abort_on_fail=False,
        )

    def bud_repeated_and_missing_public_ids_are_refused(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        violations = self.bloom.bloom_try_public_id_inserts(
            self.parameters.TAKEN_PREFIX,
            self.parameters.DUPLICATE_SUITE_ID,
            self.parameters.CAMPAIGN_EXPECTED[self.parameters.TAKEN_PREFIX][1],
        )
        self.print_variables({"refusals": violations})
        self.assertEqual(
            violations,
            [
                self.parameters.UNIQUE_VIOLATION,
                self.parameters.UNIQUE_VIOLATION,
                self.parameters.NOT_NULL_VIOLATION,
            ],
            msg=self.parameters.MSG_PUBLIC_ID_VIOLATIONS,
            abort_on_fail=False,
        )

    def bud_downgrade_keeps_the_assigned_public_ids(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.PUBLIC_ID_BEFORE)
        if code:
            self.log_info(output)
        self.assertEqual(code, 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True)
        shape = self.bloom.bloom_read_public_id_shape()
        public_ids = self.bloom.bloom_read_campaign_public_ids()
        assigned = {
            row_id: public_id
            for prefix, expected in self.parameters.CAMPAIGN_EXPECTED.items()
            for row_id, public_id in zip(self.ids[prefix], expected)
        }
        self.print_variables({"shape": shape})
        self.assertEqual(
            (shape, {row_id: public_ids[row_id] for row_id in assigned}),
            (
                {
                    "nullable": self.parameters.NULLABLE,
                    "indexes": [],
                    "revision": self.parameters.PUBLIC_ID_BEFORE,
                },
                assigned,
            ),
            msg=self.parameters.MSG_PUBLIC_ID_DOWNGRADE,
            abort_on_fail=False,
        )

    def bud_upgrading_again_restores_the_indexes(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        if code:
            self.log_info(output)
        self.assertEqual(code, 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True)
        indexes = self.bloom.bloom_read_public_id_shape()["indexes"]
        self.print_variables({"indexes": indexes})
        self.assertEqual(
            indexes,
            self.parameters.PUBLIC_ID_INDEXES,
            msg=self.parameters.MSG_PUBLIC_ID_REUPGRADE,
            abort_on_fail=False,
        )
