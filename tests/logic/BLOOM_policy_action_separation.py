"""
* @file     ${tests/logic/BLOOM_policy_action_separation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Read, write, review, approve and delete each grant their own operations and no other.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the permission functions and the policy rule validation.
"""

from tests.logic.policy_action_separation import PolicyActionSeparationBase


class PolicyActionSeparationTest(PolicyActionSeparationBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PolicyActionSeparationTest().run()
