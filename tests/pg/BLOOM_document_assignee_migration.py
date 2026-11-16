"""
* @file     ${tests/pg/BLOOM_document_assignee_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The assignee migration sets each existing workflow's assignee to its revision creator.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the upgrade from the revision before on a new PostgreSQL database holding one workflow.
"""

from tests.pg.document_assignee_migration import DocumentAssigneeMigrationBase


class DocumentAssigneeMigrationTest(DocumentAssigneeMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        before = self.parameters.ASSIGNEE_BEFORE
        self.tc_before = self.bloom.bloom_run_alembic("upgrade", before)
        self.tc_person = self.bloom.bloom_seed_workflow_of_a_creator()
        self.tc_upgrade = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.tc_assignees = self.bloom.bloom_read_workflow_assignees()
        self.tc_downgrade = self.bloom.bloom_run_alembic("downgrade", before)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentAssigneeMigrationTest().run()
