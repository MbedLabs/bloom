"""
* @file     ${tests/api/setup_api.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the first-run setup of an instance.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the first-run setup.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class SetupApiBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_an_empty_instance_needs_setup(self):
        self.bloom.bloom_new_database()
        values = self.parameters
        answer = self.bloom.bloom_api_call("GET", "/api/setup/status")
        self.assertEqual(
            (answer.status, answer.body),
            (values.STATUS_OK, {"setup_required": True}),
            msg=values.MSG_SETUP_REQUIRED,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/setup/status",
        )

    def bud_setup_creates_one_administrator_and_closes(self):
        self.bloom.bloom_new_database()
        values = self.parameters
        created, _ = self.bloom.bloom_api_setup(values.SETUP_OWNER)
        accounts = self.bloom.bloom_list_accounts()
        self.assertEqual(
            (
                created.status,
                [account[:3] for account in accounts],
                accounts[0][3] != values.SETUP_PASSWORD if accounts else None,
            ),
            (values.STATUS_CREATED, [(values.SETUP_OWNER["email"], "admin", True)], True),
            msg=values.MSG_SETUP_CREATED,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/setup",
        )
        second, _ = self.bloom.bloom_api_setup(values.SETUP_SQUATTER)
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/setup/status").body,
                second.status,
                len(self.bloom.bloom_list_accounts()),
            ),
            ({"setup_required": False}, values.STATUS_CONFLICT, 1),
            msg=values.MSG_SETUP_CLOSED,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/setup",
        )

    def bud_a_short_password_is_refused_422(self):
        self.bloom.bloom_new_database()
        values = self.parameters
        answer, _ = self.bloom.bloom_api_setup(values.SETUP_SHORT)
        self.assertEqual(
            answer.status,
            values.STATUS_UNPROCESSABLE,
            msg=values.MSG_SETUP_SHORT,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/setup",
        )

    def bud_setup_succeeds_without_mail(self):
        self.bloom.bloom_new_database()
        values = self.parameters
        answer, _ = self.bloom.bloom_api_setup(values.SETUP_OWNER, mail="unavailable")
        self.assertEqual(
            (answer.status, self.bloom.bloom_api_call("GET", "/api/setup/status").body),
            (values.STATUS_CREATED, {"setup_required": False}),
            msg=values.MSG_SETUP_NO_MAIL,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/setup",
        )

    def bud_setup_mails_the_new_administrator(self):
        self.bloom.bloom_new_database()
        values = self.parameters
        _, sent = self.bloom.bloom_api_setup(values.SETUP_OWNER)
        self.print_variables({"mail": sent})
        self.assertEqual(
            (sent.get("to_email"), sent.get("login_link", "").endswith("/login")),
            (values.SETUP_OWNER["email"], True),
            msg=values.MSG_SETUP_MAIL,
            abort_on_fail=False,
        )
