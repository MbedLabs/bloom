"""
* @file     ${tests/logic/BLOOM_response_timestamps.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Every timestamp an API response carries is serialized as UTC.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module scans the response models of app.schemas and app.api.
"""

from tests.logic.response_timestamps import ResponseTimestampsBase


class ResponseTimestampsTest(ResponseTimestampsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_models = self.bloom.bloom_response_models()
        self.tc_unmarked = self.bloom.bloom_unmarked_timestamps(self.tc_models)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ResponseTimestampsTest().run()
