"""
* @file     ${tests/pg/document_workflow_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the schema and the rows after the workflow migration.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the workflow migration on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class DocumentWorkflowMigrationBase(BloomTestCase):

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

    def bud_migrated_column_names_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["columns"],
                "differences": self.schema.found["columns"],
            }
        )
        self.assertGreater(
            self.schema.compared["columns"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["columns"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["columns"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["columns"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_column_types_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["types"],
                "differences": self.schema.found["types"],
            }
        )
        self.assertGreater(
            self.schema.compared["types"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["types"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["types"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["types"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_primary_keys_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["primary"],
                "differences": self.schema.found["primary"],
            }
        )
        self.assertGreater(
            self.schema.compared["primary"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["primary"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["primary"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["primary"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_unique_constraints_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["unique"],
                "differences": self.schema.found["unique"],
            }
        )
        self.assertGreater(
            self.schema.compared["unique"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["unique"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["unique"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["unique"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_foreign_keys_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["foreign"],
                "differences": self.schema.found["foreign"],
            }
        )
        self.assertGreater(
            self.schema.compared["foreign"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["foreign"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["foreign"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["foreign"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_check_constraints_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["checks"],
                "differences": self.schema.found["checks"],
            }
        )
        self.assertGreater(
            self.schema.compared["checks"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["checks"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["checks"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["checks"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_pending_request_index_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["pending"],
                "differences": self.schema.found["pending"],
            }
        )
        self.assertGreater(
            self.schema.compared["pending"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["pending"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["pending"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["pending"]
            ),
            abort_on_fail=False,
        )

    def bud_migrated_comment_columns_equal_the_models(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "compared": self.schema.compared["comments"],
                "differences": self.schema.found["comments"],
            }
        )
        self.assertGreater(
            self.schema.compared["comments"],
            0,
            msg=self.parameters.MSG_WORKFLOW_SCHEMA_COMPARED.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["comments"]
            ),
            abort_on_fail=False,
        )
        self.assertEqual(
            self.schema.found["comments"],
            [],
            msg=self.parameters.MSG_WORKFLOW_SCHEMA.format(
                aspect=self.parameters.WORKFLOW_SCHEMA_ASPECTS["comments"]
            ),
            abort_on_fail=False,
        )

    def bud_upgrade_leaves_the_requirement_statuses(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"before": self.rows_before.requirements, "after": self.rows_after.requirements}
        )
        self.assertEqual(
            self.rows_after.requirements,
            self.rows_before.requirements,
            msg=self.parameters.MSG_LEGACY_REQUIREMENTS,
            abort_on_fail=False,
        )

    def bud_upgrade_leaves_the_change_request_status(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.rows_after.change})
        self.assertEqual(
            self.rows_after.change,
            self.parameters.LEGACY_CHANGE_STATUS,
            msg=self.parameters.MSG_LEGACY_CHANGE,
            abort_on_fail=False,
        )

    def bud_upgrade_leaves_the_baseline_snapshot(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {"before": self.rows_before.baseline, "after": self.rows_after.baseline}
        )
        self.assertEqual(
            self.rows_after.baseline,
            self.rows_before.baseline,
            msg=self.parameters.MSG_LEGACY_BASELINE,
            abort_on_fail=False,
        )

    def bud_upgrade_creates_no_workflow_rows(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"workflows, revisions, requests": self.rows_after.workflows})
        self.assertEqual(
            self.rows_after.workflows,
            [0, 0, 0],
            msg=self.parameters.MSG_LEGACY_NO_WORKFLOWS,
            abort_on_fail=False,
        )
