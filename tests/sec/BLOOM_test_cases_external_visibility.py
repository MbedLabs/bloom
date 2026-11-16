"""
* @file     ${tests/sec/BLOOM_test_cases_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader lists customer test cases only, and a test case carries its visibility.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the test case API with one external reader, one administrator, one customer and one internal test case.
"""

from tests.sec.test_cases_external_visibility import TestCasesExternalVisibilityBase


class TestCasesExternalVisibilityTest(TestCasesExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        customer = bloom.bloom_add_test_case(
            reader.project_id,
            values.READER_CUSTOMER_TC,
            values.READER_CUSTOMER_TC,
            visibility=values.CUSTOMER_VISIBILITY,
        )
        bloom.bloom_add_test_case(
            reader.project_id,
            values.READER_INTERNAL_TC,
            values.READER_INTERNAL_TC,
            visibility=values.INTERNAL_VISIBILITY,
        )
        bloom.bloom_add_admin(values.ADMIN_EMAIL, values.API_PASSWORD)
        admin, _ = bloom.bloom_log_in(values.ADMIN_EMAIL, values.API_PASSWORD)
        self.tc_listed = bloom.bloom_api_list_test_cases(reader.headers, reader.project_id)
        self.tc_read = bloom.bloom_api_get_test_case(admin, customer)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TestCasesExternalVisibilityTest().run()
