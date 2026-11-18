"""
* @file     ${tests/logic/BLOOM_reqif_import.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A ReqIF document is parsed into objects, relations and order, and imported once with its relations as links.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the parser on a two-object document and the import into a new project per step.
"""

from tests.logic.reqif_import import ReqifImportBase


class ReqifImportTest(ReqifImportBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ReqifImportTest().run()
