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
        project_id = bloom.bloom_create_project(self.parameters.TAG_PREFIX)
        bloom.bloom_add_user(
            self.parameters.TAG_ADMIN, bloom.bloom_role(self.parameters.TAG_ADMIN_ROLE)
        )
        kind = self.parameters.TAG_KIND
        source_id, target_id = (
            bloom.bloom_add_artefact(kind, project_id=project_id, **fields)
            for fields in self.parameters.TAG_REQUIREMENTS
        )
        target = bloom.bloom_mention(kind, target_id)

        def sync(source=kind, content=target, hidden=False):
            return bloom.bloom_sync_tag_links(project_id, source, source_id, content, hidden)

        self.tc_invalid = {}
        for source, target_kind in self.parameters.TAG_INVALID_PAIRS:
            outcome = sync(source, bloom.bloom_mention(target_kind, target_id))
            self.tc_invalid[(source, target_kind)] = (outcome, bloom.bloom_list_links())
        self.tc_hidden = (sync(hidden=True), bloom.bloom_list_links())
        self.tc_self = sync(content=bloom.bloom_mention(kind, source_id))
        self.tc_first = sync()
        self.tc_links = bloom.bloom_list_links()
        self.tc_again = sync()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TagLinksTest().run()
