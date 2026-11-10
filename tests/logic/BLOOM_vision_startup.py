"""
* @file     ${tests/logic/BLOOM_vision_startup.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A restart keeps a Vision's kind and id and still repairs an unknown kind.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the startup normalization over a Vision and an unknown kind.
"""

from tests.logic.vision_startup import VisionStartupBase


class VisionStartupTest(VisionStartupBase):

    def setUpClass(self):
        super().setUpClass()
        project_id = self.bloom.bloom_create_project(self.parameters.VISION_PREFIX)
        for doc_id, doc_type, title in self.parameters.VISION_DOCUMENTS:
            self.bloom.bloom_add_document(project_id, doc_id, doc_type, title)
        self.bloom.bloom_normalize_document_kinds()
        self.tc_kinds = self.bloom.bloom_list_document_kinds()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    VisionStartupTest().run()
