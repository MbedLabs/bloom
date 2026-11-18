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
        self.bloom.bloom_start_main_api()
        self.bloom.bloom_add_admin(self.parameters.ADMIN_EMAIL, self.parameters.API_PASSWORD)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TokenConcurrencyTest().run()
