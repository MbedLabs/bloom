"""
* @file     ${tests/logic/integration_sync_outages.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests GitHub rate limits and outages during the sync.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of GitHub rate limits and outages.
"""

from budtestlibrary import parameterized

import tests.parameters as params
from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncOutagesBase(BloomTestCase):

    interface = BloomLogicInterface

    @parameterized(params.OUTAGE_CASES)
    def bud_rate_limit_or_outage_is_the_run_error(self, index):
        status, headers, body = self.parameters.OUTAGES[index]
        setting = self.bloom.bloom_get_setting(self.tc_setting_ids[index])
        found = (setting.sync_error, setting.synced_at, setting.sync_warning)
        self.print_variables(
            {"answer": (status, headers, body), "error, synced at, warning": found}
        )
        self.assertEqual(
            found,
            (self.parameters.LIST_ERROR.format(tracker="GitHub", status=status), None, None),
            msg=self.parameters.MSG_OUTAGE_ERROR,
            abort_on_fail=False,
        )
