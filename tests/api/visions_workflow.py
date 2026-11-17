"""
* @file     ${tests/api/visions_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the approval, correction and revision of a Vision.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the vision workflow.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class VisionsWorkflowBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_new_vision_is_a_controlled_draft(self):
        state = self.bloom.bloom_api_call("GET", self.path + "/workflow").body
        self.print_variables({"state": state})
        self.assertEqual(
            (state["controlled"], state["phase"], state["revisions"]),
            (True, "Draft", []),
            msg=self.parameters.MSG_VISW_DRAFT,
            abort_on_fail=False,
            method="GET",
            endpoint=self.path + "/workflow",
        )

    def bud_an_approved_vision_has_revision_one(self):
        self.bloom.bloom_api_approve_as_three_people(self.path)
        state = self.bloom.bloom_api_call("GET", self.path + "/workflow").body
        self.assertEqual(
            (state["phase"], [item["revision_number"] for item in state["revisions"]]),
            ("Approved", [1]),
            msg=self.parameters.MSG_VISW_APPROVED,
            abort_on_fail=False,
        )

    def bud_a_correction_returns_to_draft_at_the_same_revision(self):
        corrected = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{self.vision}", json={"title": "Corrected"}
        )
        state = self.bloom.bloom_api_call("GET", self.path + "/workflow").body
        self.assertEqual(
            (
                corrected.status,
                state["phase"],
                state["revision_number"],
                [item["revision_number"] for item in state["revisions"]],
            ),
            (self.parameters.STATUS_OK, "Draft", 1, [1]),
            msg=self.parameters.MSG_VISW_CORRECTED,
            abort_on_fail=False,
            method="PATCH",
            endpoint="/api/documents/{id}",
        )

    def bud_a_change_authorises_the_next_revision(self):
        values = self.parameters
        change = self.bloom.bloom_add_record("ChangeRequest", **values.VISW_CHANGE)
        link = {
            "project_id": 1,
            "source_type": "CHG",
            "source_id": change,
            "target_type": "VIS",
            "target_id": self.vision,
            "role": "impacts",
        }
        linked = self.bloom.bloom_api_call("POST", "/api/links", json=link)
        revised = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{self.vision}", json={"title": "Revised"}
        )
        state = self.bloom.bloom_api_call("GET", self.path + "/workflow").body
        self.print_variables({"state": state})
        self.assertEqual(
            (
                linked.status,
                revised.status,
                state["phase"],
                state["revision_number"],
                (state["authorizing_change"] or {}).get("id"),
                self.bloom.bloom_read_record("Document", self.vision).version,
            ),
            (values.STATUS_CREATED, values.STATUS_OK, "Draft", 2, change, "2"),
            msg=values.MSG_VISW_REVISED,
            abort_on_fail=False,
            method="PATCH",
            endpoint="/api/documents/{id}",
        )
