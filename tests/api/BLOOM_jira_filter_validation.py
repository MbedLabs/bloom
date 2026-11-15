"""
* @file     ${tests/api/BLOOM_jira_filter_validation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An integration's Jira filter accepts issue types and Bloom levels only.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests a valid filter, a blank issue type and a map to an unknown level.
"""

from tests.api.jira_filter_validation import JiraFilterValidationBase


class JiraFilterValidationTest(JiraFilterValidationBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraFilterValidationTest().run()
