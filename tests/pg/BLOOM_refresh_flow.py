"""
* @file     ${tests/pg/BLOOM_refresh_flow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The refresh cookie is set at sign-in, rotates on refresh and dies at sign-out.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database with one administrator.
"""

from tests.pg.refresh_flow import RefreshFlowBase


class RefreshFlowTest(RefreshFlowBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres()
        if not self.tc_postgres:
            return
        email, password = self.parameters.ADMIN_EMAIL, self.parameters.API_PASSWORD
        self.bloom.bloom_start_main_api()
        self.bloom.bloom_add_admin(email, password)
        self.tc_login = self.bloom.bloom_log_in_for_cookie(email, password)
        self.tc_refresh = self.bloom.bloom_refresh(self.tc_login.cookie)
        self.tc_account = self.bloom.bloom_read_account(self.tc_refresh.access_token)
        self.tc_without_cookie = self.bloom.bloom_refresh()
        self.tc_replay = self.bloom.bloom_refresh(self.tc_login.cookie)
        self.tc_second_login = self.bloom.bloom_log_in_for_cookie(email, password)
        self.tc_logout = self.bloom.bloom_log_out(self.tc_second_login.cookie)
        self.tc_after_logout = self.bloom.bloom_refresh(self.tc_second_login.cookie)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RefreshFlowTest().run()
