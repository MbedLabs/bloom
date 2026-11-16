"""
* @file     ${tests/sec/BLOOM_baselines_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets a baseline without its snapshot.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the baseline API with one external reader and one baseline that has a snapshot.
"""

from tests.sec.baselines_external_visibility import BaselinesExternalVisibilityBase


class BaselinesExternalVisibilityTest(BaselinesExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        reader = self.bloom.bloom_create_external_reader_environment()
        baseline = self.bloom.bloom_add_baseline(
            reader.project_id,
            self.parameters.READER_BASELINE_ID,
            self.parameters.BASELINE_NAME,
            self.parameters.READER_SNAPSHOT,
        )
        self.tc_answer = self.bloom.bloom_api_get_baseline(reader.headers, baseline)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    BaselinesExternalVisibilityTest().run()
