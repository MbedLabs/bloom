"""
* @file     ${tests/logic/vision_startup.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the document kind repair Bloom runs at startup.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the startup kind repair.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class VisionStartupBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_restart_keeps_vision_and_repairs_unknown_kind(self):
        self.print_variables({"before": self.parameters.VISION_DOCUMENTS, "after": self.tc_kinds})
        self.assertEqual(
            self.tc_kinds,
            self.parameters.VISION_AFTER_RESTART,
            msg=self.parameters.MSG_VISION_KEPT,
            abort_on_fail=False,
        )
