"""
* @file     ${tests/pg/BLOOM_repeated_refusals.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Refused requests sent at once from one address leave exactly one repeated refusal event.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database with 30 forged requests sent at once.
"""

from tests.pg.repeated_refusals import RepeatedRefusalsBase


class RepeatedRefusalsTest(RepeatedRefusalsBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        self.bloom.bloom_start_main_api()
        self.statuses = self.bloom.bloom_burst_forged_requests()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RepeatedRefusalsTest().run()
