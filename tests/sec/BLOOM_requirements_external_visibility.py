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
        reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        project = reader.project_id
        customer = bloom.bloom_add_requirement(
            project, values.READER_CUSTOMER_REQ, values.CUSTOMER_VISIBILITY
        )
        internal = bloom.bloom_add_requirement(
            project, values.READER_INTERNAL_REQ, values.INTERNAL_VISIBILITY
        )
        bloom.bloom_add_admin(values.ADMIN_EMAIL, values.API_PASSWORD)
        admin, _ = bloom.bloom_log_in(values.ADMIN_EMAIL, values.API_PASSWORD)
        self.tc_listed = bloom.bloom_api_list_requirements(reader.headers, project)
        self.tc_hidden = bloom.bloom_api_read_requirement(reader.headers, internal)
        self.tc_created = bloom.bloom_api_create_requirement_of_origin(
            admin, project, values.READER_NEW_TITLE, values.READER_CUSTOMER_ORIGIN
        )
        self.tc_changed = bloom.bloom_api_set_requirement_origin(
            admin, customer, values.READER_INTERNAL_ORIGIN
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementsExternalVisibilityTest().run()
