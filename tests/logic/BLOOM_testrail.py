"""
* @file     ${tests/logic/BLOOM_testrail.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    TestRail XML suites and CSV exports read into one case model, within the import limits.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the TestRail parsers on small XML and CSV exports.
"""

from tests.logic.testrail import TestrailBase


class TestrailTest(TestrailBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TestrailTest().run()
