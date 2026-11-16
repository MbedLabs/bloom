"""
* @file     ${tests/logic/BLOOM_startup_bootstrap.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The application start repairs data and seeds the administrator only when their switches are on.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the start with the repair and seed steps replaced by recorders.
"""

from tests.logic.startup_bootstrap import StartupBootstrapBase


class StartupBootstrapTest(StartupBootstrapBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    StartupBootstrapTest().run()
