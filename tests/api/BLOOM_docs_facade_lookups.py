"""
* @file     ${tests/api/BLOOM_docs_facade_lookups.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The registry finds a document of every kind by its document ID, in any letter case, with the columns of the list.
* @author   Amine El Omari
* @date     2026-11-17
* @version  1.0.0
* @note     This module tests one project holding a requirement linked to a specification and a standard.
"""

from tests.api.docs_facade_lookups import DocsFacadeLookupsBase


class DocsFacadeLookupsTest(DocsFacadeLookupsBase):

    def setUpClass(self):
        super().setUpClass()
        values = self.parameters
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.project = self.bloom.bloom_api_new_project(self.admin, values.LKP_PREFIX)
        self.requirement = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": self.project["id"], **values.LKP_REQUIREMENT},
        ).body
        self.specification = self.bloom.bloom_api_add_typed_document(
            self.admin, self.project["id"], "SPEC", values.LKP_SPECIFICATION
        ).body
        self.standard = self.bloom.bloom_api_add_typed_document(
            self.admin, self.project["id"], "STD", values.LKP_STANDARD
        ).body
        self.link_statuses = [
            self.bloom.bloom_api_link_ends(
                self.admin,
                self.project["id"],
                ("REQ", self.requirement["id"]),
                (document["doc_type"], document["id"]),
                role=values.LKP_LINK_ROLE,
            ).status
            for document in (self.specification, self.standard)
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocsFacadeLookupsTest().run()
