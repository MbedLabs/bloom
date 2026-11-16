"""
* @file     ${tests/logic/BLOOM_jira_inbound.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Jira issues map to Bloom: description text, filter, priority, references and JQL.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the mapping functions with Jira settings built in the steps.
"""

from tests.logic.jira_inbound import JiraInboundBase


class JiraInboundTest(JiraInboundBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraInboundTest().run()
