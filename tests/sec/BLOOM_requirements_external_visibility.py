"""
* @file     ${tests/sec/BLOOM_requirements_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets customer requirements only, and a requirement's origin sets its visibility.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the requirements API with one external reader, one administrator, one customer and one internal requirement.
"""

from tests.sec.requirements_external_visibility import (
    RequirementsExternalVisibilityBase,
)


class RequirementsExternalVisibilityTest(RequirementsExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        self.reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        project = self.reader.project_id
        self.customer = bloom.bloom_add_requirement(
            project, values.READER_CUSTOMER_REQ, values.CUSTOMER_VISIBILITY
        )
        self.internal = bloom.bloom_add_requirement(
            project, values.READER_INTERNAL_REQ, values.INTERNAL_VISIBILITY
        )
        bloom.bloom_add_admin(values.ADMIN_EMAIL, values.API_PASSWORD)
        self.admin, _ = bloom.bloom_log_in(values.ADMIN_EMAIL, values.API_PASSWORD)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementsExternalVisibilityTest().run()
