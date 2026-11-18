"""
* @file     ${tests/api/unhandled_errors.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the answers to errors no route handles.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the unhandled error answers.
"""

import re

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class UnhandledErrorsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_500_carries_a_reference_to_quote(self):
        answer = self.bloom.bloom_api_get_unhandled(self.parameters.UNH_PATHS["error"])
        self.print_variables({"answer": answer.body})
        self.assertEqual(
            (
                answer.status,
                bool(re.fullmatch(r"[0-9a-f]{32}", answer.reference)),
                answer.body["request_id"],
                answer.reference in answer.body["detail"],
            ),
            (self.parameters.STATUS_SERVER_ERROR, True, answer.reference, True),
            msg=self.parameters.MSG_UNH_REFERENCE,
            abort_on_fail=False,
        )
        self.assertEqual(
            (
                f"Quote reference {answer.reference} when reporting this." in answer.body["detail"],
                "Quote reference - " in answer.body["detail"],
            ),
            (True, False),
            msg=self.parameters.MSG_UNH_QUOTE,
            abort_on_fail=False,
        )

    def bud_a_500_hides_the_exception(self):
        answer = self.bloom.bloom_api_get_unhandled(self.parameters.UNH_PATHS["error"])
        self.assertEqual(
            [word in answer.text for word in ("something went bang", "RuntimeError", "Traceback")],
            [False] * 3,
            msg=self.parameters.MSG_UNH_HIDDEN,
            abort_on_fail=False,
        )

    def bud_a_lost_race_is_a_conflict_409(self):
        answer = self.bloom.bloom_api_get_unhandled(self.parameters.UNH_PATHS["unique"])
        self.print_variables({"answer": answer.body})
        self.assertEqual(
            (
                answer.status,
                answer.body["request_id"],
                answer.reference in answer.body["detail"],
                "already exists" in answer.body["detail"],
            ),
            (self.parameters.STATUS_CONFLICT, answer.reference, True, True),
            msg=self.parameters.MSG_UNH_CONFLICT,
            abort_on_fail=False,
        )
        self.assertEqual(
            [
                word in answer.text
                for word in ("projects_prefix_key", "INSERT INTO", "UniqueViolationError")
            ],
            [False] * 3,
            msg=self.parameters.MSG_UNH_CONSTRAINT,
            abort_on_fail=False,
        )

    def bud_a_row_still_referenced_is_a_conflict_409(self):
        answer = self.bloom.bloom_api_get_unhandled(self.parameters.UNH_PATHS["reference"])
        self.assertEqual(
            (answer.status, "still referenced" in answer.text),
            (self.parameters.STATUS_CONFLICT, False),
            msg=self.parameters.MSG_UNH_FOREIGN,
            abort_on_fail=False,
        )

    def bud_a_failing_commit_is_a_conflict_409(self):
        answer = self.bloom.bloom_api_get_unhandled(self.parameters.UNH_PATHS["late"])
        self.assertEqual(
            (answer.status, answer.body["request_id"], "projects_prefix_key" in answer.text),
            (self.parameters.STATUS_CONFLICT, answer.reference, False),
            msg=self.parameters.MSG_UNH_LATE,
            abort_on_fail=False,
        )

    def bud_every_route_commits_before_its_response(self):
        session_routes, late = self.bloom.bloom_session_routes()
        self.print_variables({"routes with a session": session_routes, "late": late})
        self.assertEqual(
            (session_routes > 0, late),
            (True, []),
            msg=self.parameters.MSG_UNH_COMMIT,
            abort_on_fail=False,
        )
