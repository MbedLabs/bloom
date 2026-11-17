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
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.before = self.bloom.bloom_run_alembic("upgrade", self.parameters.ASSIGNEE_BEFORE)
        self.person = self.bloom.bloom_seed_workflow_of_a_creator()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentAssigneeMigrationTest().run()
