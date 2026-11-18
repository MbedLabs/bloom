"""
* @file     ${tests/api/BLOOM_batched_lookups.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Campaigns refuse unknown and foreign suites by id, suites skip foreign test cases, and section counts stay per document.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the lookups on the full application as administrator.
"""

from tests.api.batched_lookups import BatchedLookupsBase


class BatchedLookupsTest(BatchedLookupsBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    BatchedLookupsTest().run()
