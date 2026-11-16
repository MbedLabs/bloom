"""
* @file     ${tests/sec/BLOOM_project_iam_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A member of one project gets nothing of another, and an external reader's ReqIF upload is refused.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the API with two projects, one full member and one external reader of the first.
"""

from tests.sec.project_iam_http import ProjectIamHttpBase


class ProjectIamHttpTest(ProjectIamHttpBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        password = values.API_PASSWORD
        bloom.bloom_start_full_api()
        self.allowed = bloom.bloom_create_project(values.IAMHTTP_ALLOWED_PREFIX)
        blocked = bloom.bloom_create_project(values.IAMHTTP_BLOCKED_PREFIX)
        requirement = bloom.bloom_add_requirement(
            blocked, values.IAMHTTP_BLOCKED_REQ, values.INTERNAL_VISIBILITY
        )
        member = bloom.bloom_add_account(
            values.IAMHTTP_MAINTAINER_EMAIL, password, values.API_MEMBER_ROLE
        )
        bloom.bloom_add_internal_member(self.allowed, member, values.READER_ALL_PERMISSIONS)
        external = bloom.bloom_add_account(values.EXTERNAL_EMAIL, password, values.EXTERNAL_ROLE)
        bloom.bloom_add_external_member(
            self.allowed,
            external,
            values.EXTERNAL_PERMISSIONS,
            values.CUSTOMER_VISIBILITY,
            doc_types=(),
        )
        headers, _ = bloom.bloom_log_in(values.IAMHTTP_MAINTAINER_EMAIL, password)
        self.projects = bloom.bloom_api_list_projects(headers)
        self.blocked_list = bloom.bloom_api_list_requirements(headers, blocked)
        self.blocked_read = bloom.bloom_api_read_requirement(headers, requirement)
        self.blocked_traceability = bloom.bloom_api_traceability(headers, blocked)
        self.dashboard = bloom.bloom_api_dashboard_stats(headers)
        self.blocked_import = bloom.bloom_api_import_from(
            headers, self.allowed, blocked, values.IAMHTTP_DOC_TYPE, [requirement]
        )
        reader, _ = bloom.bloom_log_in(values.EXTERNAL_EMAIL, password)
        self.reqif = bloom.bloom_api_upload_reqif(reader, self.allowed, values.IAMHTTP_REQIF)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectIamHttpTest().run()
