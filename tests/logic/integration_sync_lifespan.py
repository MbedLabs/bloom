"""
* @file     ${tests/logic/integration_sync_lifespan.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests when the application starts the integration sync loop.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the sync loop start.
"""

from budtestlibrary import parameterized

import tests.parameters as params
from tests.bloom_test_base import BloomTestCase


class IntegrationSyncLifespanBase(BloomTestCase):

    @parameterized(params.LIFESPAN_CASES)
    def bud_sync_loop_starts_unless_the_sync_is_switched_off(self, index):
        minutes, expected = self.parameters.LIFESPAN_SWITCHES[index]
        self.print_variables(
            {"INTEGRATION_SYNC_MINUTES": minutes, "loop starts": self.tc_starts[index]}
        )
        self.assertEqual(
            self.tc_starts[index], expected, msg=self.parameters.MSG_LIFESPAN, abort_on_fail=False
        )
