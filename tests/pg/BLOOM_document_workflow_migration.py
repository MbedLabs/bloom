"""
* @file     ${tests/pg/BLOOM_document_workflow_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The workflow migration creates the tables the models describe and rewrites no existing row.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the upgrade on a new PostgreSQL database holding an approved requirement, a change request and a baseline.
"""

from tests.pg.document_workflow_migration import DocumentWorkflowMigrationBase


class DocumentWorkflowMigrationTest(DocumentWorkflowMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        self.tc_before = self.bloom.bloom_run_alembic("upgrade", self.parameters.LINK_BEFORE)
        project = self.bloom.bloom_seed_requirements(
            self.parameters.LINK_PREFIX, self.parameters.LINK_REQ_IDS
        )
        self.bloom.bloom_seed_legacy_rows(project)
        self.tc_rows_before = self.bloom.bloom_read_legacy_rows()
        self.tc_upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.tc_rows_after = self.bloom.bloom_read_legacy_rows(workflows=True)
        self.tc_schema = self.bloom.bloom_compare_workflow_schema()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentWorkflowMigrationTest().run()
