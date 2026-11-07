"""
* @file     ${tests/api/artefact_activity_basics.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the REQ docs metadata and the created and updated activity events.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the basic artefact activity.
"""

from tests.bloom_test_base import BloomTestCase


class ArtefactActivityBasicsBase(BloomTestCase):

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_docs_list_gives_requirement_type_and_origin(self):
        self.print_variables({"row": self.tc_docs_row})
        self.assertEqual(
            (self.tc_docs_row or {}).get("req_type"),
            self.parameters.REQ_TYPE,
            msg=self.parameters.MSG_DOCS_REQ_METADATA,
            abort_on_fail=False,
        )
        self.assertEqual(
            (self.tc_docs_row or {}).get("req_origin"),
            self.parameters.REQ_ORIGIN,
            msg=self.parameters.MSG_DOCS_REQ_METADATA,
            abort_on_fail=False,
        )

    def bud_creating_logs_created(self):
        for kind, events in self.tc_created_events.items():
            self.print_variables({"artefact": kind, "events": events})
            self.assertIn(
                self.parameters.EVENT_CREATED,
                events or [],
                msg=self.parameters.MSG_CREATED_EVENT,
                abort_on_fail=False,
            )

    def bud_editing_a_requirement_logs_updated(self):
        self.print_variables({"events": self.tc_updated_events})
        self.assertIn(
            self.parameters.EVENT_UPDATED,
            self.tc_updated_events or [],
            msg=self.parameters.MSG_UPDATED_EVENT,
            abort_on_fail=False,
        )
