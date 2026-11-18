"""
* @file     ${tests/logic/BLOOM_link_rules.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Links follow the explicit matrix; tags reach any known kind from a prose body.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests normalization, matrix rows, roles, tag hosts and tag pairs.
"""

from tests.logic.link_rules import LinkRulesBase


class LinkRulesTest(LinkRulesBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    LinkRulesTest().run()
