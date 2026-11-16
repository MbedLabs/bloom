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
        bloom = self.bloom
        parameters = self.parameters
        self.postgres = bloom.bloom_use_postgres(tables=False)
        if not self.postgres:
            return
        self.commands = [bloom.bloom_run_alembic("upgrade", parameters.TEXT_MIGRATION_BEFORE)]
        bloom.bloom_seed_requirement_texts(
            parameters.TEXT_MIGRATION_PREFIX, parameters.TEXT_MIGRATION_ROWS
        )

        self.commands.append(bloom.bloom_run_alembic("upgrade", parameters.TEXT_MIGRATION_REVISION))
        self.upgraded = bloom.bloom_read_requirement_texts()

        self.commands.append(bloom.bloom_run_alembic("downgrade", parameters.TEXT_MIGRATION_BEFORE))
        self.downgraded = (bloom.bloom_read_revision(), bloom.bloom_read_requirement_texts())

        self.commands.append(bloom.bloom_run_alembic("upgrade", parameters.TEXT_MIGRATION_REVISION))
        self.reupgraded = (bloom.bloom_read_revision(), bloom.bloom_read_requirement_texts())

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementTextMigrationTest().run()
