"""
* @file     ${tests/api/sign_off_activity.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the review and approval activity of test cases, documents and designs.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the sign-off activity.
"""

from budtestlibrary import parameterized

import tests.parameters as params
from tests.bloom_test_base import BloomTestCase


class SignOffActivityBase(BloomTestCase):

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    @parameterized(params.SIGN_OFF_CASES)
    def bud_review_logs_reviewed(self, index):
        kind, without_update = self.parameters.SIGN_OFF_CASES_LIST[index]
        events = self.tc_reviewed_events[kind] or []
        self.print_variables({"artefact": kind, "events": events})
        self.assertIn(
            self.parameters.EVENT_REVIEWED,
            events,
            msg=self.parameters.MSG_REVIEW_LOGGED,
            abort_on_fail=False,
        )
        if without_update:
            self.assertEqual(
                events.count(self.parameters.EVENT_UPDATED),
                0,
                msg=self.parameters.MSG_REVIEW_LOGGED,
                abort_on_fail=False,
            )

    @parameterized(params.SIGN_OFF_CASES)
    def bud_approval_logs_approved(self, index):
        kind, _ = self.parameters.SIGN_OFF_CASES_LIST[index]
        self.print_variables({"artefact": kind, "events": self.tc_approved_events[kind]})
        self.assertIn(
            self.parameters.EVENT_APPROVED,
            self.tc_approved_events[kind] or [],
            msg=self.parameters.MSG_APPROVE_LOGGED,
            abort_on_fail=False,
        )

    def bud_test_case_review_fields_in_an_edit_are_refused(self):
        self.print_variables({"status": self.tc_refused})
        self.assertEqual(
            self.tc_refused,
            self.parameters.STATUS_UNPROCESSABLE,
            msg=self.parameters.MSG_REVIEW_FIELDS_REFUSED,
            abort_on_fail=False,
        )

    def bud_test_case_review_records_the_reviewer(self):
        self.print_variables({"reviewer, utc": self.tc_test_case_reviewer})
        self.assertEqual(
            self.tc_test_case_reviewer,
            (self.tc_admin_id, True),
            msg=self.parameters.MSG_REVIEW_RECORDS,
            abort_on_fail=False,
        )

    def bud_test_case_status_only_edit_logs_approved(self):
        self.print_variables({"status": self.tc_status_only, "events": self.tc_status_events})
        self.assertEqual(
            (self.tc_status_only, self.parameters.EVENT_APPROVED in (self.tc_status_events or [])),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_STATUS_ONLY_APPROVED,
            abort_on_fail=False,
        )
