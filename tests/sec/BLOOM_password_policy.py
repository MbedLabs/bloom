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
        check = self.bloom.bloom_check_password
        minimum, self.max_bytes = self.bloom.bloom_password_limits()
        filler = self.parameters.PASSWORD_FILLER
        self.minimum_input = filler * minimum
        self.minimum = check(self.minimum_input)
        lengths = dict(zip(self.parameters.PASSWORD_SHORT_LENGTHS, (0, 1, minimum - 1)))
        self.short = {label: check(filler * length) for label, length in lengths.items()}
        self.overlong = check(self.parameters.PASSWORD_OVERLONG * (self.max_bytes + 1))
        self.multibyte = check(self.parameters.PASSWORD_MULTIBYTE)
        self.schema_short = {}
        self.schema_valid = {}
        for schema, (field, base) in self.parameters.PASSWORD_SCHEMAS.items():
            self.schema_short[schema] = self.bloom.bloom_try_auth_schema(
                schema, {**base, field: self.parameters.PASSWORD_SHORT}
            )
            self.schema_valid[schema] = self.bloom.bloom_try_auth_schema(
                schema, {**base, field: self.parameters.PASSWORD_VALID}
            )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PasswordPolicyTest().run()
