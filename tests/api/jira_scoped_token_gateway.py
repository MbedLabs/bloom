"""
* @file     ${tests/api/jira_scoped_token_gateway.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests Sync now with a token Jira only takes through Atlassian's gateway.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests Sync now with a token Jira only takes through Atlassian's gateway.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraScopedTokenGatewayBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_scoped_token_pulls_through_the_gateway(self):
        self.print_variables({"created": self.tc_result.created})
        self.assertEqual(
            self.tc_result.created, 1, msg=self.parameters.MSG_GATEWAY_CREATED, abort_on_fail=False
        )

    def bud_searches_go_to_the_cloud_gateway(self):
        searches = [
            str(call)
            for call in self.bloom.site.calls
            if str(call).endswith(self.parameters.SEARCH_PATH)
        ]
        expected = f"{self.parameters.ATLASSIAN_GATEWAY}/{self.parameters.CLOUD_ID}{self.parameters.SEARCH_PATH}"
        self.print_variables({"searches": searches})
        self.assertEqual(
            searches,
            [expected, expected],
            msg=self.parameters.MSG_GATEWAY_SEARCHES,
            abort_on_fail=False,
        )

    def bud_pulled_defect_links_to_the_site(self):
        urls = [
            d.external_issue_url
            for d in self.bloom.bloom_list_defects_linked_to(self.parameters.GATEWAY_NUMBER)
        ]
        self.print_variables({"urls": urls})
        self.assertEqual(
            urls,
            [
                f"{self.parameters.JIRA_URL}/browse/{self.bloom.bloom_jira_key(self.parameters.GATEWAY_NUMBER)}"
            ],
            msg=self.parameters.MSG_GATEWAY_URL,
            abort_on_fail=False,
        )
