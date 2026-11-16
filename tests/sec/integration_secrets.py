"""
* @file     ${tests/sec/integration_secrets.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests how tracker tokens and webhook secrets are stored.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the integration secrets.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationSecretsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_envelope_starts_with_its_prefix(self):
        self.print_variables({"envelope": self.tc_envelope.value[:24]})
        self.assertEqual(
            self.tc_envelope.value[: len(self.tc_prefix)],
            self.tc_prefix,
            msg=self.parameters.MSG_SECRETS_PREFIX,
            abort_on_fail=False,
        )

    def bud_envelope_does_not_contain_the_secret(self):
        self.assertNotIn(
            self.parameters.SECRETS_TOKEN,
            self.tc_envelope.value,
            msg=self.parameters.MSG_SECRETS_HIDDEN,
            abort_on_fail=False,
        )

    def bud_envelope_decrypts_to_the_secret(self):
        self.assertEqual(
            self.tc_decrypted.value,
            self.parameters.SECRETS_TOKEN,
            msg=self.parameters.MSG_SECRETS_ROUND_TRIP,
            abort_on_fail=False,
        )

    def bud_same_secret_encrypts_differently_each_time(self):
        self.assertNotEqual(
            self.tc_second_envelope.value,
            self.tc_envelope.value,
            msg=self.parameters.MSG_SECRETS_DISTINCT,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_second_decrypted.value,
            self.tc_decrypted.value,
            msg=self.parameters.MSG_SECRETS_BOTH_DECRYPT,
            abort_on_fail=False,
        )

    def bud_encrypting_without_a_key_is_refused_503(self):
        self.assertEqual(
            self.tc_no_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_NO_KEY,
            abort_on_fail=False,
        )

    def bud_encrypting_with_a_malformed_key_is_refused_503(self):
        self.assertEqual(
            self.tc_bad_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_BAD_KEY,
            abort_on_fail=False,
        )

    def bud_decrypting_with_another_key_is_refused_503(self):
        self.assertEqual(
            self.tc_wrong_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_WRONG_KEY,
            abort_on_fail=False,
        )

    def bud_plaintext_is_refused_503(self):
        self.assertEqual(
            self.tc_plaintext.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_PLAINTEXT,
            abort_on_fail=False,
        )

    def bud_only_an_envelope_counts_as_encrypted(self):
        self.print_variables({"envelope, plaintext, nothing": self.tc_recognised})
        self.assertEqual(
            self.tc_recognised,
            (True, False, False),
            msg=self.parameters.MSG_SECRETS_RECOGNISED,
            abort_on_fail=False,
        )

    def bud_setting_is_created_201(self):
        self.print_variables({"status": self.tc_created.status, "body": self.tc_created.body})
        self.assertEqual(
            self.tc_created.status,
            self.parameters.STATUS_CREATED,
            msg=self.parameters.MSG_SECRETS_CREATED,
            abort_on_fail=False,
        )

    def bud_answer_says_the_secrets_are_set(self):
        self.assertEqual(
            (self.tc_created.body["has_token"], self.tc_created.body["has_webhook_secret"]),
            (True, True),
            msg=self.parameters.MSG_SECRETS_REPORTED,
            abort_on_fail=False,
        )

    def bud_answer_does_not_show_the_secrets(self):
        for secret in (self.parameters.SECRETS_TOKEN, self.parameters.SECRETS_WEBHOOK):
            self.assertNotIn(
                secret,
                repr(self.tc_created.body),
                msg=self.parameters.MSG_SECRETS_NOT_SHOWN.format(secret=secret),
                abort_on_fail=False,
            )

    def bud_secrets_are_stored_as_envelopes(self):
        self.print_variables({"stored": [value[:24] for value in self.tc_stored]})
        self.assertEqual(
            self.tc_stored_encrypted,
            (True, True),
            msg=self.parameters.MSG_SECRETS_STORED,
            abort_on_fail=False,
        )

    def bud_stored_envelopes_decrypt_to_what_was_sent(self):
        self.assertEqual(
            self.tc_stored_values,
            (self.parameters.SECRETS_TOKEN, self.parameters.SECRETS_WEBHOOK),
            msg=self.parameters.MSG_SECRETS_STORED_VALUES,
            abort_on_fail=False,
        )

    def bud_new_token_is_answered_200(self):
        self.assertEqual(
            self.tc_rotated.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SECRETS_ROTATED,
            abort_on_fail=False,
        )

    def bud_rotation_stores_another_envelope(self):
        self.assertNotEqual(
            self.tc_rotated_stored[0],
            self.tc_stored[0],
            msg=self.parameters.MSG_SECRETS_NEW_ENVELOPE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_rotated_value,
            self.parameters.SECRETS_ROTATED,
            msg=self.parameters.MSG_SECRETS_NEW_VALUE,
            abort_on_fail=False,
        )
