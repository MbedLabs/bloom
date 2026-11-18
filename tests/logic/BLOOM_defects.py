"""
* @file     ${tests/logic/BLOOM_defects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Defects link only by their allowed roles, issue links are read per tracker, and webhook signatures are checked.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the link rules, the issue link readers and the webhook checks.
"""

from tests.logic.defects import DefectsBase


class DefectsTest(DefectsBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DefectsTest().run()
