"""
* @file     ${tests/sec/BLOOM_token_logging.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A one-time token sent to the invite lookup never appears in the application log.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the token in the request body and in the query string.
"""

from tests.sec.token_logging import TokenLoggingBase


class TokenLoggingTest(TokenLoggingBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        path = self.parameters.INVITE_INFO_PATH
        body = {"token": self.parameters.ONE_TIME_TOKEN}
        self.tc_logs = self.bloom.bloom_api_post_and_read_logs(
            [(path, body), (f"{path}?token={self.parameters.ONE_TIME_TOKEN}", body)]
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TokenLoggingTest().run()
