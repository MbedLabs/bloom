"""
* @file     ${tests/sec/BLOOM_external_test_suites_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets customer suites only, each with its customer test cases and its last execution.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the test suite API with one external reader, a customer suite holding both test cases and an internal suite.
"""

from tests.sec.external_test_suites_visibility import ExternalTestSuitesVisibilityBase


class ExternalTestSuitesVisibilityTest(ExternalTestSuitesVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        project = reader.project_id
        customer, internal = values.CUSTOMER_VISIBILITY, values.INTERNAL_VISIBILITY
        visible = bloom.bloom_add_test_case(
            project,
            values.READER_CUSTOMER_TC,
            values.READER_CUSTOMER_TC,
            visibility=customer,
            last_execution_status=values.EXPORT_PASSED,
            last_executed_at=values.READER_EXECUTED_AT,
            last_bud_run_id=values.READER_BUD_RUN,
        )
        hidden = bloom.bloom_add_test_case(
            project, values.READER_INTERNAL_TC, values.READER_INTERNAL_TC, visibility=internal
        )
        bloom.bloom_add_test_suite(
            project, values.READER_VISIBLE_SUITE, customer, [visible, hidden]
        )
        bloom.bloom_add_test_suite(project, values.READER_HIDDEN_SUITE, internal, [visible])
        self.tc_listed = bloom.bloom_api_list_test_suites(reader.headers, project)
        self.tc_hidden = bloom.bloom_api_get_test_suite(reader.headers, values.READER_HIDDEN_SUITE)
        self.tc_visible = bloom.bloom_api_get_test_suite(
            reader.headers, values.READER_VISIBLE_SUITE
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExternalTestSuitesVisibilityTest().run()
