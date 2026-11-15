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
        self.tc_mail = self.bloom.bloom_capture_access_request_mail()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(admin, self.parameters.LABELS_PREFIX)
        requirement = self.bloom.bloom_api_create_requirement(
            admin,
            project.json()["id"],
            self.parameters.LABELS_REQUIREMENT_TITLE,
            self.parameters.REQUIREMENT_DRAFT,
        )
        self.tc_requirement = requirement.json()
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (requirement.status_code, self.parameters.STATUS_CREATED),
        ]
        members = {}
        for email, permissions in (
            (self.parameters.HIDDEN_EMAIL, self.parameters.TEST_CASE_PERMISSIONS),
            (self.parameters.READER_EMAIL, self.parameters.REQUIREMENT_PERMISSIONS),
        ):
            user = self.bloom.bloom_api_create_user(
                admin,
                email,
                self.parameters.API_PASSWORD,
                self.parameters.API_MEMBER_ROLE,
                self.parameters.MEMBER_FULL_NAME,
            )
            policy = self.bloom.bloom_api_create_policy(admin, email, permissions)
            member = self.bloom.bloom_api_add_project_member(
                admin, project.json()["id"], user.json()["id"], [policy.json()["id"]]
            )
            headers, _ = self.bloom.bloom_log_in(email, self.parameters.API_PASSWORD)
            members[email] = (user.json(), headers)
            self.tc_setup += [
                (user.status_code, self.parameters.STATUS_CREATED),
                (policy.status_code, self.parameters.STATUS_CREATED),
                (member.status_code, self.parameters.STATUS_CREATED),
            ]
        hidden_user, hidden = members[self.parameters.HIDDEN_EMAIL]
        _, reader = members[self.parameters.READER_EMAIL]

        self.tc_by_number = self.bloom.bloom_api_open_requirement_doc(
            admin, self.parameters.LABELS_PREFIX, self.tc_requirement["id"]
        )
        self.tc_by_doc_id = self.bloom.bloom_api_open_requirement_doc(
            admin, self.parameters.LABELS_PREFIX, self.tc_requirement["req_id"]
        )
        self.tc_missing = self.bloom.bloom_api_open_requirement_doc(
            admin, self.parameters.LABELS_PREFIX, self.parameters.MISSING_DOC_NUMBER
        )
        self.tc_hidden = self.bloom.bloom_api_open_requirement_doc(
            hidden, self.parameters.LABELS_PREFIX, self.tc_requirement["id"]
        )
        self.tc_reader = self.bloom.bloom_api_open_requirement_doc(
            reader, self.parameters.LABELS_PREFIX, self.tc_requirement["id"]
        )

        self.tc_admin_request = self.bloom.bloom_api_request_access(
            admin,
            self.parameters.ACCESS_REQUIREMENT,
            self.tc_requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        self.tc_mail_after_admin = len(self.tc_mail)
        self.tc_project_request = self.bloom.bloom_api_request_access(
            hidden,
            self.parameters.ACCESS_PROJECT,
            self.parameters.LABELS_PREFIX,
            self.parameters.LABELS_PREFIX,
        )
        self.tc_item_request = self.bloom.bloom_api_request_access(
            reader,
            self.parameters.ACCESS_REQUIREMENT,
            self.tc_requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        self.tc_mail_after_holders = len(self.tc_mail)

        self.tc_created = self.bloom.bloom_api_request_access(
            hidden,
            self.parameters.ACCESS_DOCUMENT,
            self.tc_requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        self.tc_mine = self.bloom.bloom_api_my_access_request(
            hidden,
            self.parameters.ACCESS_DOCUMENT,
            self.tc_requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        self.tc_gone = self.bloom.bloom_api_request_access(
            hidden,
            self.parameters.ACCESS_DOCUMENT,
            self.parameters.MISSING_DOC_NUMBER,
            self.parameters.LABELS_PREFIX,
        )
        self.tc_listed = self.bloom.bloom_api_list_access_requests(
            admin, self.parameters.LABELS_PREFIX
        )

        self.bloom.bloom_api_get_requirement(admin, self.tc_requirement["id"])
        self.bloom.bloom_api_get_user(admin, hidden_user["id"])
        self.bloom.bloom_api_get_requirement(admin, self.parameters.MISSING_REQUIREMENT_NUMBER)
        self.tc_audit = (
            self.bloom.bloom_api_audit_event(
                admin,
                self.parameters.AUDIT_REQUEST_ACTION,
                self.parameters.ACCESS_REQUIREMENT,
                self.tc_requirement["id"],
            ),
            self.bloom.bloom_api_audit_event(
                admin,
                self.parameters.AUDIT_REQUEST_ACTION,
                self.parameters.AUDIT_USER_TARGET,
                hidden_user["id"],
            ),
            self.bloom.bloom_api_audit_event(
                admin,
                self.parameters.AUDIT_REQUEST_ACTION,
                self.parameters.ACCESS_REQUIREMENT,
                self.parameters.MISSING_REQUIREMENT_NUMBER,
            ),
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessLabelsTest().run()
