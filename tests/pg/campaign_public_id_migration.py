"""
* @file     ${tests/pg/campaign_public_id_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the campaign and suite public ID migration on PostgreSQL.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the public ID migration.
"""

from tests.bloom_test_base import BloomTestCase


class CampaignPublicIdMigrationBase(BloomTestCase):

    def bud_every_alembic_command_succeeds(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for code, output in self.tc_commands:
            if code:
                self.log_info(output)
        codes = [code for code, _ in self.tc_commands]
        self.print_variables({"exit codes": codes})
        self.assertEqual(
            codes, [0] * len(codes), msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True
        )

    def bud_missing_public_ids_get_the_next_free_number(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for prefix, expected in self.parameters.CAMPAIGN_EXPECTED.items():
            found = [self.tc_public_ids[row_id] for row_id in self.tc_ids[prefix]]
            self.print_variables(
                {"seeded": self.parameters.CAMPAIGN_SEEDS[prefix], "public IDs": found}
            )
            self.assertEqual(
                found, expected, msg=self.parameters.MSG_PUBLIC_IDS_NUMBERED, abort_on_fail=False
            )

    def bud_public_ids_become_required_and_unique(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"shape": self.tc_upgraded_shape})
        self.assertEqual(
            self.tc_upgraded_shape,
            {
                "nullable": self.parameters.NOT_NULLABLE,
                "indexes": self.parameters.PUBLIC_ID_INDEXES,
                "revision": self.parameters.PUBLIC_ID_REVISION,
            },
            msg=self.parameters.MSG_PUBLIC_IDS_REQUIRED,
            abort_on_fail=False,
        )

    def bud_repeated_and_missing_public_ids_are_refused(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"refusals": self.tc_violations})
        self.assertEqual(
            self.tc_violations,
            [
                self.parameters.UNIQUE_VIOLATION,
                self.parameters.UNIQUE_VIOLATION,
                self.parameters.NOT_NULL_VIOLATION,
            ],
            msg=self.parameters.MSG_PUBLIC_ID_VIOLATIONS,
            abort_on_fail=False,
        )

    def bud_downgrade_keeps_the_assigned_public_ids(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"shape": self.tc_downgraded_shape})
        self.assertEqual(
            (self.tc_downgraded_shape, self.tc_downgraded_ids),
            (
                {
                    "nullable": self.parameters.NULLABLE,
                    "indexes": [],
                    "revision": self.parameters.PUBLIC_ID_BEFORE,
                },
                self.tc_public_ids,
            ),
            msg=self.parameters.MSG_PUBLIC_ID_DOWNGRADE,
            abort_on_fail=False,
        )

    def bud_upgrading_again_restores_the_indexes(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"indexes": self.tc_reupgraded_shape["indexes"]})
        self.assertEqual(
            self.tc_reupgraded_shape["indexes"],
            self.parameters.PUBLIC_ID_INDEXES,
            msg=self.parameters.MSG_PUBLIC_ID_REUPGRADE,
            abort_on_fail=False,
        )
