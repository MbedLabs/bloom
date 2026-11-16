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
        self.print_variables({"envelope": self.envelope.value[:24]})
        self.assertEqual(
            self.envelope.value[: len(self.prefix)],
            self.prefix,
            msg=self.parameters.MSG_SECRETS_PREFIX,
            abort_on_fail=False,
        )

    def bud_envelope_does_not_contain_the_secret(self):
        self.assertNotIn(
            self.parameters.SECRETS_TOKEN,
            self.envelope.value,
            msg=self.parameters.MSG_SECRETS_HIDDEN,
            abort_on_fail=False,
        )

    def bud_envelope_decrypts_to_the_secret(self):
        self.assertEqual(
            self.decrypted.value,
            self.parameters.SECRETS_TOKEN,
            msg=self.parameters.MSG_SECRETS_ROUND_TRIP,
            abort_on_fail=False,
        )

    def bud_same_secret_encrypts_differently_each_time(self):
        self.assertNotEqual(
            self.second_envelope.value,
            self.envelope.value,
            msg=self.parameters.MSG_SECRETS_DISTINCT,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.second_decrypted.value,
            self.decrypted.value,
            msg=self.parameters.MSG_SECRETS_BOTH_DECRYPT,
            abort_on_fail=False,
        )

    def bud_encrypting_without_a_key_is_refused_503(self):
        self.assertEqual(
            self.no_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_NO_KEY,
            abort_on_fail=False,
        )

    def bud_encrypting_with_a_malformed_key_is_refused_503(self):
        self.assertEqual(
            self.bad_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_BAD_KEY,
            abort_on_fail=False,
        )

    def bud_decrypting_with_another_key_is_refused_503(self):
        self.assertEqual(
            self.wrong_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_WRONG_KEY,
            abort_on_fail=False,
        )

    def bud_plaintext_is_refused_503(self):
        self.assertEqual(
            self.plaintext.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_PLAINTEXT,
            abort_on_fail=False,
        )

    def bud_only_an_envelope_counts_as_encrypted(self):
        self.print_variables({"envelope, plaintext, nothing": self.recognised})
        self.assertEqual(
            self.recognised,
            (True, False, False),
            msg=self.parameters.MSG_SECRETS_RECOGNISED,
            abort_on_fail=False,
        )

    def bud_setting_is_created_201(self):
        self.print_variables({"status": self.created.status, "body": self.created.body})
        self.assertEqual(
            self.created.status,
            self.parameters.STATUS_CREATED,
            msg=self.parameters.MSG_SECRETS_CREATED,
            abort_on_fail=False,
        )

    def bud_answer_says_the_secrets_are_set(self):
        self.assertEqual(
            (self.created.body["has_token"], self.created.body["has_webhook_secret"]),
            (True, True),
            msg=self.parameters.MSG_SECRETS_REPORTED,
            abort_on_fail=False,
        )

    def bud_answer_does_not_show_the_secrets(self):
        for secret in (self.parameters.SECRETS_TOKEN, self.parameters.SECRETS_WEBHOOK):
            self.assertNotIn(
                secret,
                repr(self.created.body),
                msg=self.parameters.MSG_SECRETS_NOT_SHOWN.format(secret=secret),
                abort_on_fail=False,
            )

    def bud_secrets_are_stored_as_envelopes(self):
        self.print_variables({"stored": [value[:24] for value in self.stored]})
        self.assertEqual(
            self.stored_encrypted,
            (True, True),
            msg=self.parameters.MSG_SECRETS_STORED,
            abort_on_fail=False,
        )

    def bud_stored_envelopes_decrypt_to_what_was_sent(self):
        self.assertEqual(
            self.stored_values,
            (self.parameters.SECRETS_TOKEN, self.parameters.SECRETS_WEBHOOK),
            msg=self.parameters.MSG_SECRETS_STORED_VALUES,
            abort_on_fail=False,
        )

    def bud_new_token_is_answered_200(self):
        self.assertEqual(
            self.rotated.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SECRETS_ROTATED,
            abort_on_fail=False,
        )

    def bud_rotation_stores_another_envelope(self):
        self.assertNotEqual(
            self.rotated_stored[0],
            self.stored[0],
            msg=self.parameters.MSG_SECRETS_NEW_ENVELOPE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.rotated_value,
            self.parameters.SECRETS_ROTATED,
            msg=self.parameters.MSG_SECRETS_NEW_VALUE,
            abort_on_fail=False,
        )
