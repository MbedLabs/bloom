"""
* @file     ${tests/logic/integration_sync_claim.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the claim that keeps two processes from syncing one integration.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the sync claim.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncClaimBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_first_claim_wins(self):
        claimed = self.bloom.bloom_claim(
            self.tc_setting_id, self.parameters.CLAIM_MINUTES, self.parameters.NOW
        )
        self.print_variables({"claimed": claimed})
        self.assertEqual(claimed, True, msg=self.parameters.MSG_FIRST_CLAIM, abort_on_fail=False)

    def bud_second_claim_within_the_rate_loses(self):
        claimed = self.bloom.bloom_claim(
            self.tc_setting_id, self.parameters.CLAIM_MINUTES, self.parameters.NOW
        )
        self.print_variables({"claimed": claimed})
        self.assertEqual(claimed, False, msg=self.parameters.MSG_SECOND_CLAIM, abort_on_fail=False)

    def bud_claim_after_the_rate_wins(self):
        claimed = self.bloom.bloom_claim(
            self.tc_setting_id,
            self.parameters.CLAIM_MINUTES,
            self.parameters.NOW + self.parameters.LATER,
        )
        self.print_variables({"claimed": claimed})
        self.assertEqual(claimed, True, msg=self.parameters.MSG_LATER_CLAIM, abort_on_fail=False)
