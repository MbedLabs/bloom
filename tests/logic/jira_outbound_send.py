"""
* @file     ${tests/logic/jira_outbound_send.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests new defects sent to Jira as Bugs and a defect Jira refuses.
* @author   Amine El Omari
* @date     2026-11-08
* @version  1.0.0
* @note     Base class containing the bud methods of the Bloom to Jira send.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class JiraOutboundSendBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_new_defect_becomes_a_jira_bug(self):
        sent = self.tc_created[0] if self.tc_created else {}
        found = ((sent.get("issuetype") or {}).get("name"), sent.get("summary"))
        self.print_variables({"created issues": len(self.tc_created), "first": found})
        self.assertEqual(
            found,
            (self.parameters.BUG, self.parameters.OUTBOUND_SENT_TITLE),
            msg=self.parameters.MSG_OUTBOUND_BUG,
            abort_on_fail=False,
        )

    def bud_sent_defect_links_to_its_issue(self):
        defect = self.bloom.bloom_get_defect(self.tc_sent_id)
        found = (defect.external_tracker, defect.external_issue_number)
        self.print_variables({"tracker, number": found})
        self.assertEqual(
            found,
            ("jira", self.parameters.OUTBOUND_FIRST_NUMBER),
            msg=self.parameters.MSG_OUTBOUND_LINKED,
            abort_on_fail=False,
        )

    def bud_sent_defect_logs_its_issue(self):
        events = self._events_of(self.tc_sent_id)
        self.print_variables({"events": events})
        self.assertIn(
            self.parameters.OUTBOUND_CREATED_EVENT,
            events,
            msg=self.parameters.MSG_OUTBOUND_LOGGED,
            abort_on_fail=False,
        )

    def bud_refused_defect_stays_unlinked(self):
        defect = self.bloom.bloom_get_defect(self.tc_refused_id)
        events = self._events_of(self.tc_refused_id)
        found = (defect.external_tracker, self.parameters.OUTBOUND_REFUSED_EVENT in events)
        self.print_variables({"tracker, refusal logged": found, "events": events})
        self.assertEqual(
            found, (None, True), msg=self.parameters.MSG_OUTBOUND_REFUSED, abort_on_fail=False
        )

    def _events_of(self, defect_id):
        return [
            event.event_type
            for event in self.bloom.bloom_list_defect_events()
            if event.defect_id == defect_id
        ]
