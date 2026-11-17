"""
* @file     ${tests/api/BLOOM_docs_facade_bud_links.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The document list shows each test case with the id of its last Bud run.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the document list on the full application as a project member.
"""

from tests.api.docs_facade_bud_links import DocsFacadeBudLinksBase


class DocsFacadeBudLinksTest(DocsFacadeBudLinksBase):

    def setUpClass(self):
        super().setUpClass()
        values = self.parameters
        self.bloom.bloom_start_full_api()
        project = self.bloom.bloom_create_project(values.BUDL_PREFIX)
        member = self.bloom.bloom_add_account(
            values.BUDL_MEMBER, values.API_PASSWORD, values.API_MEMBER_ROLE
        )
        self.bloom.bloom_add_internal_member(project, member, {"*": ["*"]})
        self.bloom.bloom_add_test_case(
            project, f"{values.BUDL_PREFIX}-TC-001", "Clickable Bud run", **values.BUDL_CASE
        )
        self.member, _ = self.bloom.bloom_log_in(values.BUDL_MEMBER, values.API_PASSWORD)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocsFacadeBudLinksTest().run()
