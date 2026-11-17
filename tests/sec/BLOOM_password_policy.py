"""
* @file     ${tests/sec/BLOOM_password_policy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    One password policy holds for creation, invitation, password change and reset.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the shared validator and the four request schemas.
"""

from tests.sec.password_policy import PasswordPolicyBase


class PasswordPolicyTest(PasswordPolicyBase):

    def setUpClass(self):
        super().setUpClass()
        self.minimum_length, self.max_bytes = self.bloom.bloom_password_limits()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PasswordPolicyTest().run()
