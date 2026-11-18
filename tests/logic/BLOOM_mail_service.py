"""
* @file     ${tests/logic/BLOOM_mail_service.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Mail is sent with the product sender, failures are reported without leaking content, and every mail follows one structure.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the mail service against a recording mail server.
"""

from tests.logic.mail_service import MailServiceBase


class MailServiceTest(MailServiceBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    MailServiceTest().run()
