"""
* @file     ${tests/sec/BLOOM_access_requests.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A refused user asks the administrators for access once per resource, and an administrator decides once.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the access request API with two administrators and one member.
"""

from tests.sec.access_requests import AccessRequestsBase


class AccessRequestsTest(AccessRequestsBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        password = values.API_PASSWORD
        bloom.bloom_start_full_api()
        self.sent = bloom.bloom_capture_access_request_mail()
        self.admin_id = bloom.bloom_add_admin(values.ARQ_BOSS_EMAIL, password)
        bloom.bloom_add_admin(values.ARQ_SECOND_EMAIL, password)
        self.member_id = bloom.bloom_add_account(
            values.ARQ_MEMBER_EMAIL, password, values.API_MEMBER_ROLE
        )
        self.member, _ = bloom.bloom_log_in(values.ARQ_MEMBER_EMAIL, password)
        self.admin, _ = bloom.bloom_log_in(values.ARQ_BOSS_EMAIL, password)
        self.first = bloom.bloom_api_request_access(
            self.member, values.ARQ_KIND, values.ARQ_REF, values.ARQ_PREFIX
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessRequestsTest().run()
