"""
* @file     ${tests/api/tracker_unreachable.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the answers for an unreachable issue tracker.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the unreachable tracker answers.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TrackerUnreachableBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_an_unreachable_tracker_is_a_gateway_error(self):
        for number, (failure, status) in enumerate(self.parameters.TRK_UNREACHABLE):
            defect = self.bloom.bloom_api_add_tracked_defect(
                self.admin, self.parameters.TRK_PREFIXES[number]
            )
            answer = self.bloom.bloom_api_refresh_defect_while_tracker_fails(
                self.admin, defect["id"], failure
            )
            self.print_variables({failure: answer.body})
            self.assertEqual(
                (answer.status, bool(answer.body.get("detail"))),
                (status, True),
                msg=self.parameters.MSG_TRK_UNREACHABLE.format(failure=failure, status=status),
                abort_on_fail=False,
                method="POST",
                endpoint="/api/defects/{id}/refresh-external",
            )

    def bud_the_error_names_the_tracker_and_hides_the_exception(self):
        defect = self.bloom.bloom_api_add_tracked_defect(
            self.admin, self.parameters.TRK_PREFIXES[4]
        )
        answer = self.bloom.bloom_api_refresh_defect_while_tracker_fails(
            self.admin, defect["id"], "no route to an address"
        )
        self.assertEqual(
            (
                "github" in answer.body["detail"],
                "10.0.0.5" in answer.text,
                "ConnectError" in answer.text,
            ),
            (True, False, False),
            msg=self.parameters.MSG_TRK_NAMED,
            abort_on_fail=False,
        )

    def bud_a_refusing_tracker_is_a_bad_gateway_502(self):
        defect = self.bloom.bloom_api_add_tracked_defect(
            self.admin, self.parameters.TRK_PREFIXES[5]
        )
        answer = self.bloom.bloom_api_refresh_defect_while_tracker_fails(
            self.admin, defect["id"], "refusal"
        )
        self.assertEqual(
            (answer.status, "401" in answer.body["detail"]),
            (self.parameters.STATUS_BAD_GATEWAY, True),
            msg=self.parameters.MSG_TRK_REFUSED,
            abort_on_fail=False,
        )
