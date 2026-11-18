"""
* @file     ${tests/sec/password_policy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the password policy at every entry point choosing a password.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the password policy.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class PasswordPolicyBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_minimum_length_is_accepted(self):
        minimum_input = self.parameters.PASSWORD_FILLER * self.minimum_length
        minimum = self.bloom.bloom_check_password(minimum_input)
        self.print_variables({"length": len(minimum_input), "error": minimum.error})
        self.assertEqual(
            minimum.value,
            minimum_input,
            msg=self.parameters.MSG_PASSWORD_MINIMUM,
            abort_on_fail=False,
        )

    def bud_short_passwords_are_refused(self):
        lengths = zip(self.parameters.PASSWORD_SHORT_LENGTHS, (0, 1, self.minimum_length - 1))
        for label, length in lengths:
            outcome = self.bloom.bloom_check_password(self.parameters.PASSWORD_FILLER * length)
            self.print_variables({"length": label, "error": outcome.error})
            self.assertRegex(
                outcome.error,
                self.parameters.PASSWORD_TOO_SHORT,
                msg=self.parameters.MSG_PASSWORD_SHORT,
                abort_on_fail=False,
            )

    def bud_overlong_passwords_are_refused(self):
        self.print_variables(
            {"characters": len(self.parameters.PASSWORD_MULTIBYTE), "byte limit": self.max_bytes}
        )
        self.assertLess(
            len(self.parameters.PASSWORD_MULTIBYTE),
            self.max_bytes,
            msg=self.parameters.MSG_PASSWORD_MULTIBYTE_LENGTH,
            abort_on_fail=False,
        )
        overlong = self.parameters.PASSWORD_OVERLONG * (self.max_bytes + 1)
        for password in (overlong, self.parameters.PASSWORD_MULTIBYTE):
            outcome = self.bloom.bloom_check_password(password)
            self.print_variables({"error": outcome.error})
            self.assertRegex(
                outcome.error,
                self.parameters.PASSWORD_TOO_LONG,
                msg=self.parameters.MSG_PASSWORD_LONG,
                abort_on_fail=False,
            )

    def bud_every_entry_point_refuses_a_short_password(self):
        for schema, (field, base) in self.parameters.PASSWORD_SCHEMAS.items():
            outcome = self.bloom.bloom_try_auth_schema(
                schema, {**base, field: self.parameters.PASSWORD_SHORT}
            )
            self.print_variables({"schema": schema, "error": outcome.error})
            self.assertEqual(
                outcome.error,
                self.parameters.PASSWORD_REFUSAL,
                msg=self.parameters.MSG_PASSWORD_SCHEMA_SHORT,
                abort_on_fail=False,
            )

    def bud_every_entry_point_keeps_a_valid_password(self):
        for schema, (field, base) in self.parameters.PASSWORD_SCHEMAS.items():
            outcome = self.bloom.bloom_try_auth_schema(
                schema, {**base, field: self.parameters.PASSWORD_VALID}
            )
            kept = getattr(outcome.instance, field, None)
            self.print_variables({"schema": schema, "field": field, "error": outcome.error})
            self.assertEqual(
                kept,
                self.parameters.PASSWORD_VALID,
                msg=self.parameters.MSG_PASSWORD_SCHEMA_VALID,
                abort_on_fail=False,
            )
