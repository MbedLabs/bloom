"""
* @file     ${tests/api/requirement_workflow_activity.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the activity a requirement logs through review, approval and revision.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement workflow activity.
"""

from tests.bloom_test_base import BloomTestCase


class RequirementWorkflowActivityBase(BloomTestCase):

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_review_fields_in_an_edit_are_refused(self):
        self.print_variables({"status": self.tc_refused.status_code})
        self.assertEqual(
            self.tc_refused.status_code,
            self.parameters.STATUS_UNPROCESSABLE,
            msg=self.parameters.MSG_REVIEW_FIELDS_REFUSED,
            abort_on_fail=False,
        )

    def bud_review_sign_off_records_the_reviewer(self):
        answer = self.tc_reviewed.json()
        found = (
            self.tc_reviewed.status_code,
            answer.get("reviewed_by_id"),
            str(answer.get("reviewed_at")).endswith(self.parameters.UTC_SUFFIX),
        )
        self.print_variables({"status, reviewer, utc": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.tc_admin_id, True),
            msg=self.parameters.MSG_REVIEW_RECORDS,
            abort_on_fail=False,
        )

    def bud_review_logs_reviewed_and_no_update(self):
        events = self.tc_reviewed_events or []
        self.print_variables({"events": events})
        self.assertEqual(
            (self.parameters.EVENT_REVIEWED in events, events.count(self.parameters.EVENT_UPDATED)),
            (True, 0),
            msg=self.parameters.MSG_REVIEW_LOGGED,
            abort_on_fail=False,
        )

    def bud_approval_logs_approved(self):
        self.print_variables({"events": self.tc_approved_events})
        self.assertIn(
            self.parameters.EVENT_APPROVED,
            self.tc_approved_events or [],
            msg=self.parameters.MSG_APPROVE_LOGGED,
            abort_on_fail=False,
        )

    def bud_status_only_edit_logs_approved(self):
        self.print_variables({"status": self.tc_status_only, "events": self.tc_status_events})
        self.assertEqual(
            (self.tc_status_only, self.parameters.EVENT_APPROVED in (self.tc_status_events or [])),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_STATUS_ONLY_APPROVED,
            abort_on_fail=False,
        )

    def bud_content_and_status_edit_is_refused(self):
        self.print_variables({"status": self.tc_mixed})
        self.assertEqual(
            self.tc_mixed,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_MIXED_EDIT_REFUSED,
            abort_on_fail=False,
        )

    def bud_edit_under_an_approved_change_starts_a_revision(self):
        events = self.tc_revision_events or []
        found = (
            self.tc_edited.status_code,
            self.tc_edited.json().get("status"),
            self.parameters.EVENT_UPDATED in events,
            self.parameters.EVENT_REVISION in events,
        )
        self.print_variables({"status, record status, updated, revision": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.parameters.STATUS_DRAFT, True, True),
            msg=self.parameters.MSG_REVISION_STARTED,
            abort_on_fail=False,
        )
