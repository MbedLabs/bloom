"""
* @file     ${tests/logic/startup_bootstrap.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what the application start runs for each switch setting.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the application start.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class StartupBootstrapBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_both_switches_off_runs_nothing(self):
        calls = self.bloom.bloom_startup_calls(repair=False, seed_admin=False)
        self.print_variables({"calls": calls})
        self.assertEqual(calls, [], msg=self.parameters.MSG_STB_NEITHER, abort_on_fail=False)

    def bud_the_repair_switch_runs_the_repair_steps(self):
        calls = self.bloom.bloom_startup_calls(repair=True, seed_admin=False)
        self.print_variables({"calls": calls})
        self.assertEqual(
            calls,
            self.parameters.STB_REPAIR_STEPS,
            msg=self.parameters.MSG_STB_REPAIR,
            abort_on_fail=False,
        )

    def bud_the_seed_switch_seeds_the_administrator(self):
        calls = self.bloom.bloom_startup_calls(repair=False, seed_admin=True)
        self.print_variables({"calls": calls})
        self.assertEqual(
            calls,
            [self.parameters.STB_SEED_STEP],
            msg=self.parameters.MSG_STB_SEED,
            abort_on_fail=False,
        )

    def bud_both_switches_run_repair_then_seed(self):
        calls = self.bloom.bloom_startup_calls(repair=True, seed_admin=True)
        self.print_variables({"calls": calls})
        self.assertEqual(
            calls,
            [*self.parameters.STB_REPAIR_STEPS, self.parameters.STB_SEED_STEP],
            msg=self.parameters.MSG_STB_BOTH,
            abort_on_fail=False,
        )
