"""
* @file     ${tests/logic/BLOOM_tag_links.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Tags become reference links; invalid pairs are refused, hidden and self tags skipped.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     This module tests the tag sync of one requirement body tagging another.
"""

from tests.logic.tag_links import TagLinksBase


class TagLinksTest(TagLinksBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        self.project_id = bloom.bloom_create_project(self.parameters.TAG_PREFIX)
        bloom.bloom_add_user(
            self.parameters.TAG_ADMIN, bloom.bloom_role(self.parameters.TAG_ADMIN_ROLE)
        )
        self.source_id, self.target_id = (
            bloom.bloom_add_artefact(self.parameters.TAG_KIND, project_id=self.project_id, **fields)
            for fields in self.parameters.TAG_REQUIREMENTS
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TagLinksTest().run()
