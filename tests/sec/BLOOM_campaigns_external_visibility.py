"""
* @file     ${tests/sec/BLOOM_campaigns_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets customer campaigns only, and a synchronised result updates the item without giving the campaign a run.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the campaign API with one external reader, one full member, a customer campaign holding both test cases and both suites, and an internal campaign.
"""

from tests.sec.campaigns_external_visibility import CampaignsExternalVisibilityBase


class CampaignsExternalVisibilityTest(CampaignsExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(doc_types=None)
        project = reader.project_id
        customer, internal = values.CUSTOMER_VISIBILITY, values.INTERNAL_VISIBILITY
        visible_tc = bloom.bloom_add_test_case(
            project, values.READER_CUSTOMER_TC, values.READER_CUSTOMER_TC, visibility=customer
        )
        hidden_tc = bloom.bloom_add_test_case(
            project, values.READER_INTERNAL_TC, values.READER_INTERNAL_TC, visibility=internal
        )
        visible_suite = bloom.bloom_add_test_suite(
            project, values.READER_VISIBLE_SUITE, customer, []
        )
        hidden_suite = bloom.bloom_add_test_suite(project, values.READER_HIDDEN_SUITE, internal, [])
        executed = {
            **values.READER_CAMPAIGN_EXECUTED,
            "executed_at": values.READER_CAMPAIGN_EXECUTED_AT,
        }
        bloom.bloom_add_campaign(
            project,
            values.READER_VISIBLE_CAMPAIGN,
            customer,
            [visible_suite, hidden_suite],
            [(visible_tc, executed), (hidden_tc, values.READER_CAMPAIGN_PENDING)],
        )
        bloom.bloom_add_campaign(
            project,
            values.READER_HIDDEN_CAMPAIGN,
            internal,
            [],
            [(visible_tc, values.READER_CAMPAIGN_PENDING)],
        )
        self.tc_listed = bloom.bloom_api_list_campaigns(reader.headers, project)
        self.tc_hidden = bloom.bloom_api_get_campaign(reader.headers, values.READER_HIDDEN_CAMPAIGN)
        self.tc_visible = bloom.bloom_api_get_campaign(
            reader.headers, values.READER_VISIBLE_CAMPAIGN
        )
        email, password = values.READER_MAINTAINER_EMAIL, values.API_PASSWORD
        member = bloom.bloom_add_account(email, password, values.API_MEMBER_ROLE)
        bloom.bloom_add_internal_member(project, member, values.READER_ALL_PERMISSIONS)
        headers, _ = bloom.bloom_log_in(email, password)
        bloom.bloom_allow_bud_sync()
        result = {
            "tc_id": values.READER_CUSTOMER_TC,
            "status": values.EXPORT_PASSED,
            "comment": values.READER_SYNC_COMMENT,
            "executed_at": values.READER_SYNC_AT,
            "bud_run_id": values.READER_SYNC_RUN,
        }
        self.tc_synced = bloom.bloom_api_sync_results(headers, [result])
        self.tc_after_sync = bloom.bloom_api_get_campaign(headers, values.READER_VISIBLE_CAMPAIGN)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CampaignsExternalVisibilityTest().run()
