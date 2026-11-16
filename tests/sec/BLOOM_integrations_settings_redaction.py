"""
* @file     ${tests/sec/BLOOM_integrations_settings_redaction.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The tracker settings an external reader lists report set secrets without their values.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the settings API with one external reader and one GitHub setting.
"""

from tests.sec.integrations_settings_redaction import IntegrationsSettingsRedactionBase


class IntegrationsSettingsRedactionTest(IntegrationsSettingsRedactionBase):

    def setUpClass(self):
        super().setUpClass()
        reader = self.bloom.bloom_create_external_reader_environment()
        self.bloom.bloom_create_webhook_integration(
            reader.project_id, tracker=self.parameters.READER_TRACKER
        )
        self.answer = self.bloom.bloom_api_list_settings(reader.headers, reader.project_id)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    IntegrationsSettingsRedactionTest().run()
