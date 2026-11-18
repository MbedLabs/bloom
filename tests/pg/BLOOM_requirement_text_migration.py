"""
* @file     ${tests/pg/BLOOM_requirement_text_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Each requirement's editor text moves into its description and the editor content is cleared.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     This module tests the migration on new PostgreSQL seeded at the revision before.
"""

from tests.pg.requirement_text_migration import RequirementTextMigrationBase


class RequirementTextMigrationTest(RequirementTextMigrationBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.before = self.bloom.bloom_run_alembic("upgrade", self.parameters.TEXT_MIGRATION_BEFORE)
        self.bloom.bloom_seed_requirement_texts(
            self.parameters.TEXT_MIGRATION_PREFIX, self.parameters.TEXT_MIGRATION_ROWS
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementTextMigrationTest().run()
