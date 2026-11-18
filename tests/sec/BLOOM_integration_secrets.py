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
        self.envelope = bloom.bloom_encrypt_secret(secret)
        self.decrypted = bloom.bloom_decrypt_secret(self.envelope.value)
        bloom.bloom_start_full_api()
        bloom.bloom_add_admin(values.ADMIN_EMAIL, values.API_PASSWORD)
        self.headers, _ = bloom.bloom_log_in(values.ADMIN_EMAIL, values.API_PASSWORD)
        project = bloom.bloom_create_project()
        self.created = bloom.bloom_api_create_setting(
            self.headers, project, values.SECRETS_TRACKER, secret, values.SECRETS_WEBHOOK
        )
        self.setting = self.created.body["id"]
        self.stored = bloom.bloom_read_setting_secrets(self.setting)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationSecretsTest().run()
