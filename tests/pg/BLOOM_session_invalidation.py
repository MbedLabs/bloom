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
        old, new = self.parameters.SESSION_OLD_PASSWORD, self.parameters.SESSION_NEW_PASSWORD
        role = self.parameters.SESSION_ROLE
        self.bloom.bloom_start_main_api()
        email = self.parameters.SESSION_CHANGE_EMAIL
        self.bloom.bloom_add_account(email, old, role)
        login = self.bloom.bloom_log_in_for_cookie(email, old)
        self.change_before = self.bloom.bloom_read_account(login.access_token).status
        self.change = self.bloom.bloom_change_password(login.access_token, old, new)
        self.change_after = self.bloom.bloom_probe_sessions(login, email, old, new)
        email = self.parameters.SESSION_RESET_EMAIL
        self.bloom.bloom_add_account(email, old, role)
        login = self.bloom.bloom_log_in_for_cookie(email, old)
        self.reset_before = self.bloom.bloom_read_account(login.access_token).status
        self.reset_mail = self.bloom.bloom_request_password_reset(email)
        self.reset = self.bloom.bloom_reset_password(self.reset_mail.token, new)
        self.reset_after = self.bloom.bloom_probe_sessions(login, email, old, new)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SessionInvalidationTest().run()
