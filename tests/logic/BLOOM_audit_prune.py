"""
* @file     ${tests/logic/BLOOM_audit_prune.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The audit prune command removes only events older than the retention it is given.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests a prune over one old and one recent event.
"""

from tests.logic.audit_prune import AuditPruneBase


class AuditPruneTest(AuditPruneBase):

    def setUpClass(self):
        super().setUpClass()
        for action, age_days in self.parameters.AUDIT_EVENTS:
            self.bloom.bloom_add_audit_event(action, age_days)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AuditPruneTest().run()
