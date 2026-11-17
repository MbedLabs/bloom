"""
* @file     ${tests/pg/BLOOM_session_invalidation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A password change and a password reset end every session the account had.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database with two accounts, one per way of changing the password.
"""

from tests.pg.session_invalidation import SessionInvalidationBase


class SessionInvalidationTest(SessionInvalidationBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        values = self.parameters
        self.bloom.bloom_start_main_api()
        for email in (values.SESSION_CHANGE_EMAIL, values.SESSION_RESET_EMAIL):
            self.bloom.bloom_add_account(email, values.SESSION_OLD_PASSWORD, values.SESSION_ROLE)
        self.change_login = self.bloom.bloom_log_in_for_cookie(
            values.SESSION_CHANGE_EMAIL, values.SESSION_OLD_PASSWORD
        )
        self.reset_login = self.bloom.bloom_log_in_for_cookie(
            values.SESSION_RESET_EMAIL, values.SESSION_OLD_PASSWORD
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SessionInvalidationTest().run()
