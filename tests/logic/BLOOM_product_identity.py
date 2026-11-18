"""
* @file     ${tests/logic/BLOOM_product_identity.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Bloom names itself Bloom PLM by EmbedLabs, and no setting or environment value renames it.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the identity constants, three mails, the API title and the settings.
"""

from tests.logic.product_identity import ProductIdentityBase


class ProductIdentityTest(ProductIdentityBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProductIdentityTest().run()
