"""
* @file     ${tests/api/baseline_read_admission.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests baseline reads of a group member whose group is not admitted.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the baseline read admission.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class BaselineReadAdmissionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_group_without_admission_denies_both_reads(self):
        self.print_variables({"list, detail": self.tc_reads})
        self.assertEqual(
            self.tc_reads,
            self.parameters.BOTH_READS_DENIED,
            msg=self.parameters.MSG_GROUP_NEEDS_ADMISSION,
            abort_on_fail=False,
        )
