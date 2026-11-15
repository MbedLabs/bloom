"""
* @file     ${tests/logic/audit_prune.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the audit prune command against its retention.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the audit prune.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AuditPruneBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_prune_removes_the_old_event(self):
        self.print_variables(
            {"retention": self.parameters.AUDIT_RETENTION_DAYS, "removed": self.tc_removed}
        )
        self.assertEqual(
            self.tc_removed,
            self.parameters.AUDIT_REMOVED,
            msg=self.parameters.MSG_AUDIT_REMOVED,
            abort_on_fail=False,
        )

    def bud_prune_keeps_the_recent_event(self):
        self.print_variables({"left": self.tc_left})
        self.assertEqual(
            self.tc_left,
            self.parameters.AUDIT_LEFT,
            msg=self.parameters.MSG_AUDIT_LEFT,
            abort_on_fail=False,
        )
