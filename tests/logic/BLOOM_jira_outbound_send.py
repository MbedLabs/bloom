"""
* @file     ${tests/logic/BLOOM_jira_outbound_send.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Sync now sends new defects to Jira as Bugs and links them; a refused one stays unlinked.
* @author   Amine El Omari
* @date     2026-11-08
* @version  1.0.0
* @note     This module tests two new defects on a Bloom to Jira integration, Jira refusing the second.
"""

from tests.logic.jira_outbound_send import JiraOutboundSendBase


class JiraOutboundSendTest(JiraOutboundSendBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_project_id = self.bloom.bloom_create_project()
        self.tc_setting_id = self.bloom.bloom_create_integration(
            self.tc_project_id, direction=self.parameters.OUTBOUND_DIRECTION
        )
        self.bloom.bloom_mark_sends_since(self.parameters.OUTBOUND_MARKER)
        self.tc_sent_id = self.bloom.bloom_add_unlinked_defect(
            self.tc_project_id, self.parameters.OUTBOUND_SENT_TITLE
        )
        self.tc_refused_id = self.bloom.bloom_add_unlinked_defect(
            self.tc_project_id, self.parameters.OUTBOUND_REFUSED_TITLE
        )
        self.tc_created = self.bloom.bloom_serve_jira_creation(
            self.parameters.OUTBOUND_FIRST_NUMBER, refuse_after=1
        )
        self.bloom.bloom_send_now(self.tc_setting_id)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraOutboundSendTest().run()
