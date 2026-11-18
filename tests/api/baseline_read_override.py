"""
* @file     ${tests/api/baseline_read_override.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests baseline reads under a group admission and a project override.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the baseline read override.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class BaselineReadOverrideBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.setup})
        self.assertEqual(
            [found for found, _ in self.setup],
            [expected for _, expected in self.setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_admitted_group_allows_both_reads(self):
        self.print_variables({"list, detail": self.admitted})
        self.assertEqual(
            self.admitted,
            self.parameters.BOTH_READS_ALLOWED,
            msg=self.parameters.MSG_GROUP_ADMITTED_READS,
            abort_on_fail=False,
        )

    def bud_override_without_baseline_read_denies_both(self):
        self.print_variables({"list, detail": self.overridden})
        self.assertEqual(
            self.overridden,
            self.parameters.BOTH_READS_DENIED,
            msg=self.parameters.MSG_OVERRIDE_DENIES,
            abort_on_fail=False,
        )

    def bud_override_with_baseline_read_allows_both(self):
        listed, detail = self.bloom.bloom_api_read_baselines(
            self.member, self.project_id, self.baseline_id
        )
        allowed = (
            [listed.status_code, detail.status_code],
            self.baseline_id in [item["id"] for item in listed.json()],
            detail.json().get("id"),
        )
        self.print_variables({"allowed": allowed})
        self.assertEqual(
            allowed,
            (self.parameters.BOTH_READS_ALLOWED, True, self.baseline_id),
            msg=self.parameters.MSG_OVERRIDE_ALLOWS,
            abort_on_fail=False,
        )

    def bud_other_project_stays_denied(self):
        other = [
            answer.status_code
            for answer in self.bloom.bloom_api_read_baselines(
                self.member, self.other_project_id, self.other_baseline_id
            )
        ]
        self.print_variables({"list, detail": other})
        self.assertEqual(
            other,
            self.parameters.BOTH_READS_DENIED,
            msg=self.parameters.MSG_OTHER_PROJECT_DENIED,
            abort_on_fail=False,
        )

    def bud_group_keeps_its_policy(self):
        group_policies = self.bloom.bloom_api_get_group(self.admin, self.group_id).json()[
            "policy_ids"
        ]
        self.print_variables({"group policies": group_policies})
        self.assertEqual(
            group_policies,
            [self.baseline_policy_id],
            msg=self.parameters.MSG_GROUP_POLICY_KEPT,
            abort_on_fail=False,
        )
