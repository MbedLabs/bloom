"""
* @file     ${tests/api/baseline_read_owner.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests baseline reads of the admin and of a project owner.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the baseline read owner authority.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class BaselineReadOwnerBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.setup})
        self.assertEqual(
            [found for found, _ in self.setup],
            [expected for _, expected in self.setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_admin_and_owner_read_the_baseline(self):
        for actor, headers in (("admin", self.admin), ("owner", self.owner)):
            listed, detail = self.bloom.bloom_api_read_baselines(
                headers, self.project_id, self.baseline_id
            )
            reads = (
                [listed.status_code, detail.status_code],
                self.baseline_id in [item["id"] for item in listed.json()],
                detail.json().get("id"),
            )
            self.print_variables({"actor": actor, "reads": reads})
            self.assertEqual(
                reads,
                (self.parameters.BOTH_READS_ALLOWED, True, self.baseline_id),
                msg=self.parameters.MSG_OWNER_AUTHORITY,
                abort_on_fail=False,
            )
