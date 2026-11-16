"""
* @file     ${tests/pg/BLOOM_token_concurrency.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A refresh cookie, a reset token, an invitation and a verification token each work once when used six times at once.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database, each token sent in six requests at once.
"""

from tests.pg.token_concurrency import TokenConcurrencyBase


class TokenConcurrencyTest(TokenConcurrencyBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        password, role = self.parameters.API_PASSWORD, self.parameters.SESSION_ROLE
        new_password = self.parameters.SESSION_NEW_PASSWORD
        self.bloom.bloom_start_main_api()
        self.bloom.bloom_add_admin(self.parameters.ADMIN_EMAIL, password)
        admin = self.bloom.bloom_log_in_for_cookie(self.parameters.ADMIN_EMAIL, password)
        self.refresh_token = admin.cookie
        self.refresh_statuses = self.bloom.bloom_race_requests(
            "/api/auth/refresh", cookie=admin.cookie
        )
        admin = self.bloom.bloom_log_in_for_cookie(self.parameters.ADMIN_EMAIL, password)
        email = self.parameters.TOKEN_RACE_RESET_EMAIL
        self.bloom.bloom_add_account(email, password, role)
        self.reset_token = self.bloom.bloom_request_password_reset(email).token
        self.reset_statuses = self.bloom.bloom_race_requests(
            "/api/auth/reset-password",
            json={"token": self.reset_token, "new_password": new_password},
        )
        self.invite_token = self.bloom.bloom_invite(
            admin.access_token, self.parameters.TOKEN_RACE_INVITE_EMAIL, role
        ).token
        self.invite_statuses = self.bloom.bloom_race_requests(
            "/api/auth/accept-invite",
            json={"token": self.invite_token, "password": new_password},
        )
        email = self.parameters.TOKEN_RACE_VERIFY_EMAIL
        self.bloom.bloom_add_account(email, password, role)
        member = self.bloom.bloom_log_in_for_cookie(email, password)
        self.verify_token = self.bloom.bloom_request_verification(member.access_token).token
        self.verify_statuses = self.bloom.bloom_race_requests(
            "/api/auth/verify-email", json={"token": self.verify_token}
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TokenConcurrencyTest().run()
