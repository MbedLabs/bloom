"""
* @file     ${tests/logic/BLOOM_isolation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Loading the test configuration replaces inherited credentials and refuses external mail, dotenv files and non-test databases.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the configuration in new Python processes started with made-up inherited credentials.
"""

from tests.logic.isolation import IsolationBase


class IsolationTest(IsolationBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IsolationTest().run()
