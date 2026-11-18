"""
* @file     ${tests/sec/integrations_settings_redaction.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what an external reader gets of the tracker settings.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the tracker settings an external reader lists.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class IntegrationsSettingsRedactionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_the_one_setting_200(self):
        self.print_variables({"status": self.answer.status, "body": self.answer.body})
        self.assertEqual(
            (self.answer.status, len(self.answer.body)),
            (self.parameters.STATUS_OK, 1),
            msg=self.parameters.MSG_READER_SETTINGS,
            abort_on_fail=False,
        )

    def bud_setting_says_the_secrets_are_set(self):
        self.assertEqual(
            tuple(
                self.answer.body[0][key] for key in ("tracker", "has_token", "has_webhook_secret")
            ),
            (self.parameters.READER_TRACKER, True, True),
            msg=self.parameters.MSG_READER_SETTING_FLAGS,
            abort_on_fail=False,
        )

    def bud_setting_does_not_contain_the_webhook_secret(self):
        self.assertNotIn(
            self.parameters.READER_SECRET_FIELD,
            self.answer.body[0],
            msg=self.parameters.MSG_READER_NO_SECRET,
            abort_on_fail=False,
        )
