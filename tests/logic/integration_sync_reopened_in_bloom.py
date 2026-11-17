"""
* @file     ${tests/logic/integration_sync_reopened_in_bloom.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a defect reopened in Bloom while its GitHub issue stays closed.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of a defect reopened in Bloom.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncReopenedInBloomBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_defect_reopened_in_bloom_stays_open(self):
        synced = self.bloom.bloom_run_sync(self.parameters.NOW)
        status = self.bloom.bloom_get_defect(self.defect_id).status
        self.print_variables({"synced": synced, "defect": status})
        self.assertEqual(
            status,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_REOPENED_IN_BLOOM_KEPT,
            abort_on_fail=False,
        )
