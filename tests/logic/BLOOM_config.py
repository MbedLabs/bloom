"""
* @file     ${tests/logic/BLOOM_config.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Settings read BLOOM_ names before plain names, keep their limits, and production refuses bootstrap defaults.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the settings on a cleared environment with the variables of each case.
"""

from tests.logic.config import ConfigBase


class ConfigTest(ConfigBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ConfigTest().run()
