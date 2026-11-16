"""
* @file     ${tests/logic/BLOOM_default_policy_catalogue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The default catalogue covers Bloom resources with independently scoped permissions and frozen release groups.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the catalogue and the release and Visions migrations that froze it.
"""

from tests.logic.default_policy_catalogue import DefaultPolicyCatalogueBase


class DefaultPolicyCatalogueTest(DefaultPolicyCatalogueBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DefaultPolicyCatalogueTest().run()
