"""
* @file     ${tests/sec/baselines_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what an external reader gets of a baseline.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the baseline an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class BaselinesExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_reads_the_baseline_200(self):
        self.print_variables({"status": self.tc_answer.status, "body": self.tc_answer.body})
        self.assertEqual(
            self.tc_answer.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_READER_BASELINE,
            abort_on_fail=False,
        )

    def bud_external_reader_gets_no_snapshot(self):
        self.assertEqual(
            self.tc_answer.body["snapshot"],
            None,
            msg=self.parameters.MSG_READER_NO_SNAPSHOT,
            abort_on_fail=False,
        )
