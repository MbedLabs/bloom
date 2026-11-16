"""
* @file     ${tests/sec/BLOOM_request_audit.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Every HTTP request leaves one api.request record with its actor, client, route, status and outcome.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application with one administrator, one member without access, and one project with a design.
"""

from tests.sec.request_audit import RequestAuditBase


class RequestAuditTest(RequestAuditBase):

    def setUpClass(self):
        super().setUpClass()
        values, bloom = self.parameters, self.bloom
        bloom.bloom_start_full_api()
        self.admin_id = bloom.bloom_add_account(
            values.RQA_ADMIN, values.API_PASSWORD, values.EMAIL_ADMIN_ROLE
        )
        self.member_id = bloom.bloom_add_account(
            values.RQA_MEMBER, values.API_PASSWORD, values.API_MEMBER_ROLE
        )
        self.admin, _ = bloom.bloom_log_in(values.RQA_ADMIN, values.API_PASSWORD)
        self.member, _ = bloom.bloom_log_in(values.RQA_MEMBER, values.API_PASSWORD)
        self.project = bloom.bloom_create_project(values.RQA_PREFIX)
        self.design = bloom.bloom_add_design(self.project, values.RQA_DESIGN)
        bloom.bloom_add_exploding_route(values.RQA_EXPLODING_PATH, values.RQA_EXPLOSION)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequestAuditTest().run()
