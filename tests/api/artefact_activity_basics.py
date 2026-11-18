"""
* @file     ${tests/api/artefact_activity_basics.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the REQ docs metadata and the created and updated activity events.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the basic artefact activity.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactActivityBasicsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.setup})
        self.assertEqual(
            [found for found, _ in self.setup],
            [expected for _, expected in self.setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_docs_list_gives_requirement_type_and_origin(self):
        self.print_variables({"row": self.docs_row})
        self.assertEqual(
            (self.docs_row or {}).get("req_type"),
            self.parameters.REQ_TYPE,
            msg=self.parameters.MSG_DOCS_REQ_METADATA,
            abort_on_fail=False,
        )
        self.assertEqual(
            (self.docs_row or {}).get("req_origin"),
            self.parameters.REQ_ORIGIN,
            msg=self.parameters.MSG_DOCS_REQ_METADATA,
            abort_on_fail=False,
        )

    def bud_creating_logs_created(self):
        for kind, events in self.created_events.items():
            self.print_variables({"artefact": kind, "events": events})
            self.assertIn(
                self.parameters.EVENT_CREATED,
                events or [],
                msg=self.parameters.MSG_CREATED_EVENT,
                abort_on_fail=False,
            )

    def bud_editing_a_requirement_logs_updated(self):
        updated_events = self.bloom.bloom_api_activity_types(
            self.admin, self.parameters.REQUIREMENT_KIND, self.typed_id
        )
        self.print_variables({"events": updated_events})
        self.assertIn(
            self.parameters.EVENT_UPDATED,
            updated_events or [],
            msg=self.parameters.MSG_UPDATED_EVENT,
            abort_on_fail=False,
        )
