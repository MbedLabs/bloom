"""
* @file     ${tests/logic/config.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests how the settings are read from the environment.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the settings.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ConfigBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_reqif_limits_have_their_defaults(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_REQIF_DEFAULTS)
        expected = self.parameters.CFG_REQIF_DEFAULTS_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_REQIF_DEFAULTS,
            abort_on_fail=False,
        )

    def bud_the_attachment_upload_limits_have_their_defaults(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_UPLOAD_DEFAULTS)
        expected = self.parameters.CFG_UPLOAD_DEFAULTS_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_UPLOAD_DEFAULTS,
            abort_on_fail=False,
        )

    def bud_the_attachment_upload_limits_read_the_bloom_names(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_UPLOAD_PREFIXED)
        expected = self.parameters.CFG_UPLOAD_PREFIXED_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_UPLOAD_PREFIXED,
            abort_on_fail=False,
        )

    def bud_two_concurrent_uploads_per_user_are_refused(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_UPLOAD_CONCURRENCY)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (loaded, self.parameters.CFG_UPLOAD_CONCURRENCY_REFUSAL in (refusal or "no refusal")),
            (None, True),
            msg=self.parameters.MSG_CFG_UPLOAD_CONCURRENCY,
            abort_on_fail=False,
        )

    def bud_a_reqif_member_limit_above_25_mib_is_refused(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_MEMBER_LIMIT)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (loaded, self.parameters.CFG_MEMBER_LIMIT_REFUSAL in (refusal or "no refusal")),
            (None, True),
            msg=self.parameters.MSG_CFG_MEMBER_LIMIT,
            abort_on_fail=False,
        )

    def bud_settings_read_the_bloom_names(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PREFIXED)
        expected = self.parameters.CFG_PREFIXED_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PREFIXED,
            abort_on_fail=False,
        )

    def bud_the_mail_sender_name_is_not_a_setting(self):
        loaded, _ = self.bloom.bloom_load_settings(self.parameters.CFG_PREFIXED)
        self.assertEqual(
            hasattr(loaded, "SMTP_FROM_NAME"),
            False,
            msg=self.parameters.MSG_CFG_SENDER_NAME,
            abort_on_fail=False,
        )

    def bud_settings_fall_back_to_the_plain_names(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PLAIN)
        expected = self.parameters.CFG_PLAIN_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PLAIN,
            abort_on_fail=False,
        )

    def bud_the_bloom_name_wins_over_the_plain_name(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_BOTH)
        expected = self.parameters.CFG_BOTH_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_BOTH,
            abort_on_fail=False,
        )

    def bud_cli_code_mode_is_off_by_default(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_CLI_DEFAULT)
        expected = self.parameters.CFG_CLI_DEFAULT_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_CLI_DEFAULT,
            abort_on_fail=False,
        )

    def bud_cli_code_mode_reads_the_bloom_name(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_CLI_PREFIXED)
        expected = self.parameters.CFG_CLI_PREFIXED_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_CLI_PREFIXED,
            abort_on_fail=False,
        )

    def bud_cli_code_mode_reads_the_plain_name(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_CLI_PLAIN)
        expected = self.parameters.CFG_CLI_PLAIN_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_CLI_PLAIN,
            abort_on_fail=False,
        )

    def bud_cli_code_mode_prefers_the_bloom_name(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_CLI_BOTH)
        expected = self.parameters.CFG_CLI_BOTH_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_CLI_BOTH,
            abort_on_fail=False,
        )

    def bud_production_refuses_the_default_admin_email(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_EMAIL)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (loaded, self.parameters.CFG_PROD_EMAIL_REFUSAL in (refusal or "no refusal")),
            (None, True),
            msg=self.parameters.MSG_CFG_PROD_EMAIL,
            abort_on_fail=False,
        )

    def bud_production_refuses_the_default_admin_password(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_PASSWORD)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (loaded, self.parameters.CFG_PROD_PASSWORD_REFUSAL in (refusal or "no refusal")),
            (None, True),
            msg=self.parameters.MSG_CFG_PROD_PASSWORD,
            abort_on_fail=False,
        )

    def bud_production_refuses_a_short_admin_password(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_SHORT)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (loaded, self.parameters.CFG_PROD_SHORT_REFUSAL in (refusal or "no refusal")),
            (None, True),
            msg=self.parameters.MSG_CFG_PROD_SHORT,
            abort_on_fail=False,
        )

    def bud_development_allows_the_bootstrap_defaults(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_DEV_DEFAULTS)
        expected = self.parameters.CFG_DEV_DEFAULTS_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_DEV_DEFAULTS,
            abort_on_fail=False,
        )

    def bud_development_seeds_and_repairs_by_default(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_DEV_SWITCHES)
        expected = self.parameters.CFG_DEV_SWITCHES_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_DEV_SWITCHES,
            abort_on_fail=False,
        )

    def bud_production_neither_seeds_nor_repairs_by_default(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_SWITCHES)
        expected = self.parameters.CFG_PROD_SWITCHES_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PROD_SWITCHES,
            abort_on_fail=False,
        )

    def bud_production_can_turn_the_seed_on(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_SEED)
        expected = self.parameters.CFG_PROD_SEED_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PROD_SEED,
            abort_on_fail=False,
        )

    def bud_production_can_turn_the_repair_on(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_REPAIR)
        expected = self.parameters.CFG_PROD_REPAIR_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PROD_REPAIR,
            abort_on_fail=False,
        )

    def bud_production_starts_without_an_integration_key(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_NO_KEY)
        expected = self.parameters.CFG_PROD_NO_KEY_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PROD_NO_KEY,
            abort_on_fail=False,
        )

    def bud_production_starts_with_an_unusable_integration_key(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_PROD_BAD_KEY)
        expected = self.parameters.CFG_PROD_BAD_KEY_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_PROD_BAD_KEY,
            abort_on_fail=False,
        )

    def bud_production_starts_with_a_valid_integration_key(self):
        env = {
            **self.parameters.CFG_PRODUCTION,
            "BLOOM_INTEGRATION_ENCRYPTION_KEY": self.bloom.bloom_new_encryption_key(),
        }
        loaded, refusal = self.bloom.bloom_load_settings(env)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, ["BLOOM_ENV"]),
            {"BLOOM_ENV": "production"},
            msg=self.parameters.MSG_CFG_PROD_GOOD_KEY,
            abort_on_fail=False,
        )

    def bud_development_starts_without_an_integration_key(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_DEV_NO_KEY)
        expected = self.parameters.CFG_DEV_NO_KEY_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_DEV_NO_KEY,
            abort_on_fail=False,
        )

    def bud_the_frontend_address_fills_a_missing_app_address(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_LEGACY_URL)
        expected = self.parameters.CFG_LEGACY_URL_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_LEGACY_URL,
            abort_on_fail=False,
        )

    def bud_the_app_address_wins_over_the_frontend_address(self):
        loaded, refusal = self.bloom.bloom_load_settings(self.parameters.CFG_APP_URL)
        expected = self.parameters.CFG_APP_URL_EXPECTED
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            self.bloom.bloom_read_settings(loaded, expected),
            expected,
            msg=self.parameters.MSG_CFG_APP_URL,
            abort_on_fail=False,
        )
