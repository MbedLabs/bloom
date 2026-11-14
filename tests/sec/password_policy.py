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
        self.print_variables({"length": len(self.tc_minimum_input), "error": self.tc_minimum.error})
        self.assertEqual(
            self.tc_minimum.value,
            self.tc_minimum_input,
            msg=self.parameters.MSG_PASSWORD_MINIMUM,
            abort_on_fail=False,
        )

    def bud_short_passwords_are_refused(self):
        for label, outcome in self.tc_short.items():
            self.print_variables({"length": label, "error": outcome.error})
            self.assertRegex(
                outcome.error,
                self.parameters.PASSWORD_TOO_SHORT,
                msg=self.parameters.MSG_PASSWORD_SHORT,
                abort_on_fail=False,
            )

    def bud_overlong_passwords_are_refused(self):
        self.print_variables(
            {"characters": len(self.parameters.PASSWORD_MULTIBYTE), "byte limit": self.tc_max_bytes}
        )
        self.assertLess(
            len(self.parameters.PASSWORD_MULTIBYTE),
            self.tc_max_bytes,
            msg=self.parameters.MSG_PASSWORD_MULTIBYTE_LENGTH,
            abort_on_fail=False,
        )
        for outcome in (self.tc_overlong, self.tc_multibyte):
            self.print_variables({"error": outcome.error})
            self.assertRegex(
                outcome.error,
                self.parameters.PASSWORD_TOO_LONG,
                msg=self.parameters.MSG_PASSWORD_LONG,
                abort_on_fail=False,
            )

    def bud_every_entry_point_refuses_a_short_password(self):
        for schema, outcome in self.tc_schema_short.items():
            self.print_variables({"schema": schema, "error": outcome.error})
            self.assertEqual(
                outcome.error,
                self.parameters.PASSWORD_REFUSAL,
                msg=self.parameters.MSG_PASSWORD_SCHEMA_SHORT,
                abort_on_fail=False,
            )

    def bud_every_entry_point_keeps_a_valid_password(self):
        for schema, (field, _) in self.parameters.PASSWORD_SCHEMAS.items():
            outcome = self.tc_schema_valid[schema]
            kept = getattr(outcome.instance, field, None)
            self.print_variables({"schema": schema, "field": field, "error": outcome.error})
            self.assertEqual(
                kept,
                self.parameters.PASSWORD_VALID,
                msg=self.parameters.MSG_PASSWORD_SCHEMA_VALID,
                abort_on_fail=False,
            )
