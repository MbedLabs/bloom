"""
* @file     ${tests/sec/BLOOM_integration_secrets.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Tracker tokens and webhook secrets are encrypted at rest and never returned.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the encryption functions and the settings API with one administrator and one project.
"""

from tests.sec.integration_secrets import IntegrationSecretsBase


class IntegrationSecretsTest(IntegrationSecretsBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        secret = values.SECRETS_TOKEN
        self.tc_prefix = bloom.bloom_envelope_prefix()
        self.tc_envelope = bloom.bloom_encrypt_secret(secret)
        self.tc_decrypted = bloom.bloom_decrypt_secret(self.tc_envelope.value)
        self.tc_second_envelope = bloom.bloom_encrypt_secret(secret)
        self.tc_second_decrypted = bloom.bloom_decrypt_secret(self.tc_second_envelope.value)
        self.tc_no_key = bloom.bloom_encrypt_secret(secret, key="")
        self.tc_bad_key = bloom.bloom_encrypt_secret(secret, key=values.SECRETS_MALFORMED_KEY)
        self.tc_wrong_key = bloom.bloom_decrypt_secret(
            self.tc_envelope.value, key=bloom.bloom_new_encryption_key()
        )
        self.tc_plaintext = bloom.bloom_decrypt_secret(values.SECRETS_PLAINTEXT)
        self.tc_recognised = (
            bloom.bloom_is_encrypted(self.tc_envelope.value),
            bloom.bloom_is_encrypted(values.SECRETS_PLAINTEXT),
            bloom.bloom_is_encrypted(None),
        )
        bloom.bloom_start_full_api()
        bloom.bloom_add_admin(values.ADMIN_EMAIL, values.API_PASSWORD)
        headers, _ = bloom.bloom_log_in(values.ADMIN_EMAIL, values.API_PASSWORD)
        project = bloom.bloom_create_project()
        self.tc_created = bloom.bloom_api_create_setting(
            headers, project, values.SECRETS_TRACKER, secret, values.SECRETS_WEBHOOK
        )
        setting = self.tc_created.body["id"]
        self.tc_stored = bloom.bloom_read_setting_secrets(setting)
        self.tc_stored_encrypted = tuple(bloom.bloom_is_encrypted(v) for v in self.tc_stored)
        self.tc_stored_values = tuple(bloom.bloom_decrypt_secret(v).value for v in self.tc_stored)
        self.tc_rotated = bloom.bloom_api_rotate_setting_token(
            headers, setting, values.SECRETS_ROTATED
        )
        self.tc_rotated_stored = bloom.bloom_read_setting_secrets(setting)
        self.tc_rotated_value = bloom.bloom_decrypt_secret(self.tc_rotated_stored[0]).value

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSecretsTest().run()
