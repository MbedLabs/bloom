"""
* @file     ${tests/pg/BLOOM_integrity_conflict.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A unique constraint violated on flush is answered as a conflict that hides the constraint.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database, with one route that flushes two projects of one prefix.
"""

from tests.pg.integrity_conflict import IntegrityConflictBase


class IntegrityConflictTest(IntegrityConflictBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        self.bloom.bloom_start_main_api()
        self.bloom.bloom_add_conflicting_route()
        self.answer = self.bloom.bloom_api_post(self.parameters.CONFLICT_PATH)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrityConflictTest().run()
