"""
* @file     ${tests/api/BLOOM_perf_traceability.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Traceability, coverage gaps and requirement detail are read with a bounded number of statements.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the reads on the full application as administrator, counting the statements of one request.
"""

from tests.api.perf_traceability import PerfTraceabilityBase


class PerfTraceabilityTest(PerfTraceabilityBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PerfTraceabilityTest().run()
