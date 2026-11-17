"""
* @file     ${tests/api/BLOOM_docs_facade_registry.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The registry filters, searches, sorts and pages a project's documents in SQL, and answers for named rows.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the registry of one project holding two requirements and two test cases with links and a review.
"""

from tests.api.docs_facade_registry import DocsFacadeRegistryBase


class DocsFacadeRegistryTest(DocsFacadeRegistryBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()
        self.registry = self.bloom.bloom_api_seed_registry(
            self.admin, self.parameters.REG_PREFIXES[3]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocsFacadeRegistryTest().run()
