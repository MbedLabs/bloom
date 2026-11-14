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
        self.tc_postgres = bloom.bloom_use_postgres(tables=False)
        if not self.tc_postgres:
            return
        self.tc_commands = [bloom.bloom_run_alembic("upgrade", parameters.TEXT_MIGRATION_BEFORE)]
        bloom.bloom_seed_requirement_texts(
            parameters.TEXT_MIGRATION_PREFIX, parameters.TEXT_MIGRATION_ROWS
        )

        self.tc_commands.append(
            bloom.bloom_run_alembic("upgrade", parameters.TEXT_MIGRATION_REVISION)
        )
        self.tc_upgraded = bloom.bloom_read_requirement_texts()

        self.tc_commands.append(
            bloom.bloom_run_alembic("downgrade", parameters.TEXT_MIGRATION_BEFORE)
        )
        self.tc_downgraded = (bloom.bloom_read_revision(), bloom.bloom_read_requirement_texts())

        self.tc_commands.append(
            bloom.bloom_run_alembic("upgrade", parameters.TEXT_MIGRATION_REVISION)
        )
        self.tc_reupgraded = (bloom.bloom_read_revision(), bloom.bloom_read_requirement_texts())

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementTextMigrationTest().run()
