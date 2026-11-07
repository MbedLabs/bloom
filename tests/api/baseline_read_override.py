"""
* @file     ${tests/api/baseline_read_override.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests baseline reads under a group admission and a project override.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the baseline read override.
"""

from tests.bloom_test_base import BloomTestCase


class BaselineReadOverrideBase(BloomTestCase):

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_admitted_group_allows_both_reads(self):
        self.print_variables({"list, detail": self.tc_admitted})
        self.assertEqual(
            self.tc_admitted,
            self.parameters.BOTH_READS_ALLOWED,
            msg=self.parameters.MSG_GROUP_ADMITTED_READS,
            abort_on_fail=False,
        )

    def bud_override_without_baseline_read_denies_both(self):
        self.print_variables({"list, detail": self.tc_overridden})
        self.assertEqual(
            self.tc_overridden,
            self.parameters.BOTH_READS_DENIED,
            msg=self.parameters.MSG_OVERRIDE_DENIES,
            abort_on_fail=False,
        )

    def bud_override_with_baseline_read_allows_both(self):
        self.print_variables({"allowed": self.tc_allowed})
        self.assertEqual(
            self.tc_allowed,
            (self.parameters.BOTH_READS_ALLOWED, True, self.tc_baseline_id),
            msg=self.parameters.MSG_OVERRIDE_ALLOWS,
            abort_on_fail=False,
        )

    def bud_other_project_stays_denied(self):
        self.print_variables({"list, detail": self.tc_other})
        self.assertEqual(
            self.tc_other,
            self.parameters.BOTH_READS_DENIED,
            msg=self.parameters.MSG_OTHER_PROJECT_DENIED,
            abort_on_fail=False,
        )

    def bud_group_keeps_its_policy(self):
        self.print_variables({"group policies": self.tc_group_policies})
        self.assertEqual(
            self.tc_group_policies,
            [self.tc_baseline_policy_id],
            msg=self.parameters.MSG_GROUP_POLICY_KEPT,
            abort_on_fail=False,
        )
