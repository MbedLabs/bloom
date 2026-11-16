"""
* @file     ${tests/pg/repeated_refusals.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a burst of refused requests from one address.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the repeated refusals on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class RepeatedRefusalsBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_every_forged_request_is_refused_401(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"statuses": sorted(set(self.tc_statuses))})
        self.assertEqual(
            self.tc_statuses,
            [self.parameters.STATUS_UNAUTHORIZED] * self.parameters.REFUSAL_REQUESTS,
            msg=self.parameters.MSG_REFUSAL_STATUSES,
            abort_on_fail=False,
        )

    def bud_every_refusal_is_recorded_for_the_address(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"denied api.request events": self.tc_denied})
        self.assertEqual(
            self.tc_denied,
            self.parameters.REFUSAL_REQUESTS,
            msg=self.parameters.MSG_REFUSAL_RECORDED,
            abort_on_fail=False,
        )

    def bud_burst_is_larger_than_the_threshold(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"threshold": self.tc_threshold})
        self.assertGreater(
            self.parameters.REFUSAL_REQUESTS,
            self.tc_threshold,
            msg=self.parameters.MSG_REFUSAL_OVER_THRESHOLD,
            abort_on_fail=False,
        )

    def bud_burst_leaves_one_repeated_refusals_event(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"repeated refusal events": self.tc_detected})
        self.assertEqual(
            self.tc_detected,
            1,
            msg=self.parameters.MSG_REFUSAL_ONE_EVENT,
            abort_on_fail=False,
        )
