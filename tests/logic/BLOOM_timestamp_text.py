"""
* @file     ${tests/logic/BLOOM_timestamp_text.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Times for people are UTC to the minute; stored execution times are UTC.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests naive, missing and zoned times and a server in another zone.
"""

from tests.logic.timestamp_text import TimestampTextBase


class TimestampTextTest(TimestampTextBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_naive = self.bloom.bloom_minute_utc(self.parameters.STAMP_NAIVE)
        self.tc_none = self.bloom.bloom_minute_utc(None)
        self.tc_aware = self.bloom.bloom_minute_utc(self.parameters.STAMP_AWARE)
        self.tc_stored = self.bloom.bloom_resolve_execution_time_in_zone(
            self.parameters.STAMP_EXECUTED, self.parameters.STAMP_SERVER_ZONE
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TimestampTextTest().run()
