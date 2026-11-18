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
        prefix = self.bloom.bloom_envelope_prefix()
        self.print_variables({"envelope": self.envelope.value[:24], "prefix": prefix})
        self.assertEqual(
            self.envelope.value[: len(prefix)],
            prefix,
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
        second_envelope = self.bloom.bloom_encrypt_secret(self.parameters.SECRETS_TOKEN)
        second_decrypted = self.bloom.bloom_decrypt_secret(second_envelope.value)
        self.print_variables({"envelope": second_envelope.value[:24]})
        self.assertNotEqual(
            second_envelope.value,
            self.envelope.value,
            msg=self.parameters.MSG_SECRETS_DISTINCT,
            abort_on_fail=False,
        )
        self.assertEqual(
            second_decrypted.value,
            self.decrypted.value,
            msg=self.parameters.MSG_SECRETS_BOTH_DECRYPT,
            abort_on_fail=False,
        )

    def bud_encrypting_without_a_key_is_refused_503(self):
        no_key = self.bloom.bloom_encrypt_secret(
            self.parameters.SECRETS_TOKEN, key=self.parameters.SECRETS_NO_KEY
        )
        self.print_variables({"status": no_key.status})
        self.assertEqual(
            no_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_NO_KEY,
            abort_on_fail=False,
        )

    def bud_encrypting_with_a_malformed_key_is_refused_503(self):
        bad_key = self.bloom.bloom_encrypt_secret(
            self.parameters.SECRETS_TOKEN, key=self.parameters.SECRETS_MALFORMED_KEY
        )
        self.print_variables({"status": bad_key.status})
        self.assertEqual(
            bad_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_BAD_KEY,
            abort_on_fail=False,
        )

    def bud_decrypting_with_another_key_is_refused_503(self):
        wrong_key = self.bloom.bloom_decrypt_secret(
            self.envelope.value, key=self.bloom.bloom_new_encryption_key()
        )
        self.print_variables({"status": wrong_key.status})
        self.assertEqual(
            wrong_key.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_WRONG_KEY,
            abort_on_fail=False,
        )

    def bud_plaintext_is_refused_503(self):
        plaintext = self.bloom.bloom_decrypt_secret(self.parameters.SECRETS_PLAINTEXT)
        self.print_variables({"status": plaintext.status})
        self.assertEqual(
            plaintext.status,
            self.parameters.SECRETS_UNAVAILABLE,
            msg=self.parameters.MSG_SECRETS_PLAINTEXT,
            abort_on_fail=False,
        )

    def bud_only_an_envelope_counts_as_encrypted(self):
        recognised = (
            self.bloom.bloom_is_encrypted(self.envelope.value),
            self.bloom.bloom_is_encrypted(self.parameters.SECRETS_PLAINTEXT),
            self.bloom.bloom_is_encrypted(None),
        )
        self.print_variables({"envelope, plaintext, nothing": recognised})
        self.assertEqual(
            recognised,
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
        stored_encrypted = tuple(self.bloom.bloom_is_encrypted(value) for value in self.stored)
        self.print_variables({"stored": [value[:24] for value in self.stored]})
        self.assertEqual(
            stored_encrypted,
            (True, True),
            msg=self.parameters.MSG_SECRETS_STORED,
            abort_on_fail=False,
        )

    def bud_stored_envelopes_decrypt_to_what_was_sent(self):
        stored_values = tuple(self.bloom.bloom_decrypt_secret(value).value for value in self.stored)
        self.print_variables({"stored": stored_values})
        self.assertEqual(
            stored_values,
            (self.parameters.SECRETS_TOKEN, self.parameters.SECRETS_WEBHOOK),
            msg=self.parameters.MSG_SECRETS_STORED_VALUES,
            abort_on_fail=False,
        )

    def bud_new_token_is_answered_200(self):
        rotated = self.bloom.bloom_api_rotate_setting_token(
            self.headers, self.setting, self.parameters.SECRETS_ROTATED
        )
        self.print_variables({"status": rotated.status, "body": rotated.body})
        self.assertEqual(
            rotated.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SECRETS_ROTATED,
            abort_on_fail=False,
        )

    def bud_rotation_stores_another_envelope(self):
        rotated_stored = self.bloom.bloom_read_setting_secrets(self.setting)
        rotated_value = self.bloom.bloom_decrypt_secret(rotated_stored[0]).value
        self.print_variables({"stored": rotated_stored[0][:24]})
        self.assertNotEqual(
            rotated_stored[0],
            self.stored[0],
            msg=self.parameters.MSG_SECRETS_NEW_ENVELOPE,
            abort_on_fail=False,
        )
        self.assertEqual(
            rotated_value,
            self.parameters.SECRETS_ROTATED,
            msg=self.parameters.MSG_SECRETS_NEW_VALUE,
            abort_on_fail=False,
        )
