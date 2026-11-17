"""
* @file     ${tests/api/BLOOM_access_labels.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Documents open by database id, holders are refused access requests, targets are labelled.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests one requirement, a member who may not read it and one who may.
"""

from tests.api.access_labels import AccessLabelsBase


class AccessLabelsTest(AccessLabelsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.mail = self.bloom.bloom_capture_access_request_mail()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(self.admin, self.parameters.LABELS_PREFIX)
        requirement = self.bloom.bloom_api_create_requirement(
            self.admin,
            project.json()["id"],
            self.parameters.LABELS_REQUIREMENT_TITLE,
            self.parameters.REQUIREMENT_DRAFT,
        )
        self.requirement = requirement.json()
        self.setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (requirement.status_code, self.parameters.STATUS_CREATED),
        ]
        members = {}
        for email, permissions in (
            (self.parameters.HIDDEN_EMAIL, self.parameters.TEST_CASE_PERMISSIONS),
            (self.parameters.READER_EMAIL, self.parameters.REQUIREMENT_PERMISSIONS),
        ):
            user = self.bloom.bloom_api_create_user(
                self.admin,
                email,
                self.parameters.API_PASSWORD,
                self.parameters.API_MEMBER_ROLE,
                self.parameters.MEMBER_FULL_NAME,
            )
            policy = self.bloom.bloom_api_create_policy(self.admin, email, permissions)
            member = self.bloom.bloom_api_add_project_member(
                self.admin, project.json()["id"], user.json()["id"], [policy.json()["id"]]
            )
            headers, _ = self.bloom.bloom_log_in(email, self.parameters.API_PASSWORD)
            members[email] = (user.json(), headers)
            self.setup += [
                (user.status_code, self.parameters.STATUS_CREATED),
                (policy.status_code, self.parameters.STATUS_CREATED),
                (member.status_code, self.parameters.STATUS_CREATED),
            ]
        self.hidden_user, self.hidden = members[self.parameters.HIDDEN_EMAIL]
        _, self.reader = members[self.parameters.READER_EMAIL]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessLabelsTest().run()
