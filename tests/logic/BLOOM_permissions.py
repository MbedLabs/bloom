"""
* @file     ${tests/logic/BLOOM_permissions.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Role baselines, policy merges, wildcards and transitions grant the expected actions.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the permission functions against fixed tables.
"""

from tests.logic.permissions import PermissionsBase


class PermissionsTest(PermissionsBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PermissionsTest().run()
