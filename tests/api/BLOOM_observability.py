"""
* @file     ${tests/api/BLOOM_observability.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Each request gets an id and one audit event, metrics are exposed in the Prometheus format, and logs are JSON.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the observability middleware on a small application with one ping route.
"""

from tests.api.observability import ObservabilityBase


class ObservabilityTest(ObservabilityBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_observed_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ObservabilityTest().run()
