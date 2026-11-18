"""
* @file     ${tests/api/BLOOM_sign_off_activity.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Test cases, documents and designs log their review and approval sign-offs.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests one test case, one document and one design reviewed and approved.
"""

from tests.api.sign_off_activity import SignOffActivityBase


class SignOffActivityTest(SignOffActivityBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.admin_id = self.bloom.bloom_api_me(self.admin)
        project = self.bloom.bloom_api_create_project(self.admin, self.parameters.ACTIVITY_PREFIX)
        project_id = project.json()["id"]
        self.setup = [(project.status_code, self.parameters.STATUS_CREATED)]
        self.reviewed_events = {}
        self.approved_events = {}
        for kind, _ in self.parameters.SIGN_OFF_CASES_LIST:
            created = self.bloom.bloom_api_create_artefact(
                self.admin, kind, project_id, self.parameters.ARTEFACT_TITLE
            )
            artefact_id = created.json()["id"]
            review_setup, reviewed = self.bloom.bloom_api_review(
                self.admin, kind, artefact_id, self.admin_id
            )
            self.reviewed_events[kind] = self.bloom.bloom_api_activity_types(
                self.admin, kind, artefact_id
            )
            approved = self.bloom.bloom_api_sign_off(
                self.admin, kind, artefact_id, self.parameters.APPROVE_STEP
            )
            self.approved_events[kind] = self.bloom.bloom_api_activity_types(
                self.admin, kind, artefact_id
            )
            if kind == self.parameters.TEST_CASE_KIND:
                self.test_case_id = artefact_id
                self.test_case_reviewer = (
                    reviewed.json().get("reviewed_by_id"),
                    str(reviewed.json().get("reviewed_at")).endswith(self.parameters.UTC_SUFFIX),
                )
            self.setup += [
                (created.status_code, self.parameters.STATUS_CREATED),
                (review_setup, self.parameters.REVIEW_SETUP_EXPECTED),
                (reviewed.status_code, self.parameters.STATUS_OK),
                (approved.status_code, self.parameters.STATUS_OK),
            ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SignOffActivityTest().run()
