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

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TimestampTextTest().run()
