"""
* @file     ${tests/logic/product_identity.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that Bloom names itself Bloom PLM by EmbedLabs everywhere.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the product identity.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ProductIdentityBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_identity_constants_are_fixed(self):
        self.assertEqual(
            self.bloom.bloom_identity(),
            (
                self.parameters.PID_NAME,
                self.parameters.PID_IDENTITY,
                self.parameters.PID_POWERED_BY,
            ),
            msg=self.parameters.MSG_PID_CONSTANTS,
            abort_on_fail=False,
        )

    def bud_the_invitation_names_bloom_plm(self):
        mail = self.bloom.bloom_capture_mail("send_invite_email", **self.parameters.PID_INVITE)[0]
        self.print_variables({"subject": mail["subject"]})
        self.assertEqual(
            (
                mail["subject"],
                "<title>Bloom PLM by EmbedLabs</title>" in mail["html"],
                "Welcome to Bloom PLM by EmbedLabs</h1>" in mail["html"],
                "join the Bloom PLM platform" in mail["text"],
            ),
            ("You're invited to Bloom PLM", True, True, True),
            msg=self.parameters.MSG_PID_INVITE,
            abort_on_fail=False,
        )

    def bud_the_access_request_mail_carries_the_identity(self):
        mail = self.bloom.bloom_capture_mail(
            "send_access_request_email", **self.parameters.PID_ACCESS
        )[0]
        self.print_variables({"subject": mail["subject"]})
        self.assertEqual(
            (
                mail["subject"],
                "<title>Bloom PLM by EmbedLabs</title>" in mail["html"],
                "${app_identity}" in mail["html"],
            ),
            ("Access requested on Bloom PLM: Requirements", True, False),
            msg=self.parameters.MSG_PID_ACCESS,
            abort_on_fail=False,
        )

    def bud_the_email_change_authorization_names_bloom_plm(self):
        mail = self.bloom.bloom_capture_mail(
            "send_email_change_authorization_email", **self.parameters.PID_AUTHORIZATION
        )[0]
        phrase = self.parameters.PID_SEPARATE_LINK
        self.assertEqual(
            (phrase in mail["text"], phrase in mail["html"]),
            (True, True),
            msg=self.parameters.MSG_PID_AUTHORIZATION,
            abort_on_fail=False,
        )

    def bud_the_api_title_is_the_fixed_identity(self):
        self.assertEqual(
            self.bloom.bloom_api_identity(),
            (self.parameters.PID_IDENTITY, "Backend API for Bloom PLM by EmbedLabs"),
            msg=self.parameters.MSG_PID_API,
            abort_on_fail=False,
        )

    def bud_the_app_name_is_not_a_setting(self):
        result = self.bloom.bloom_app_name_setting(self.parameters.PID_RENAMED)
        self.print_variables({"a field, an attribute": result})
        self.assertEqual(
            result, (False, False), msg=self.parameters.MSG_PID_NOT_A_SETTING, abort_on_fail=False
        )

    def bud_an_app_name_in_the_environment_does_not_rename_the_app(self):
        title = self.bloom.bloom_title_with_app_name(self.parameters.PID_RENAMED)
        self.print_variables({"title": title})
        self.assertEqual(
            title,
            self.parameters.PID_IDENTITY,
            msg=self.parameters.MSG_PID_ENVIRONMENT,
            abort_on_fail=False,
        )
