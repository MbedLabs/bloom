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
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.tc_admin_id = self.bloom.bloom_api_me(admin)
        project = self.bloom.bloom_api_create_project(admin, self.parameters.ACTIVITY_PREFIX)
        project_id = project.json()["id"]
        self.tc_setup = [(project.status_code, self.parameters.STATUS_CREATED)]
        self.tc_reviewed_events = {}
        self.tc_approved_events = {}
        for kind, _ in self.parameters.SIGN_OFF_CASES_LIST:
            created = self.bloom.bloom_api_create_artefact(
                admin, kind, project_id, self.parameters.ARTEFACT_TITLE
            )
            artefact_id = created.json()["id"]
            if kind == self.parameters.TEST_CASE_KIND:
                self.tc_refused = self.bloom.bloom_api_update_artefact(
                    admin,
                    kind,
                    artefact_id,
                    {
                        "reviewed_by_id": self.tc_admin_id,
                        "reviewed_at": self.parameters.FORGED_REVIEWED_AT,
                    },
                ).status_code
            review_setup, reviewed = self.bloom.bloom_api_review(
                admin, kind, artefact_id, self.tc_admin_id
            )
            self.tc_reviewed_events[kind] = self.bloom.bloom_api_activity_types(
                admin, kind, artefact_id
            )
            approved = self.bloom.bloom_api_sign_off(
                admin, kind, artefact_id, self.parameters.APPROVE_STEP
            )
            self.tc_approved_events[kind] = self.bloom.bloom_api_activity_types(
                admin, kind, artefact_id
            )
            if kind == self.parameters.TEST_CASE_KIND:
                self.tc_test_case_reviewer = (
                    reviewed.json().get("reviewed_by_id"),
                    str(reviewed.json().get("reviewed_at")).endswith(self.parameters.UTC_SUFFIX),
                )
                self.tc_status_only = self.bloom.bloom_api_update_artefact(
                    admin, kind, artefact_id, {"status": self.parameters.STATUS_APPROVED}
                ).status_code
                self.tc_status_events = self.bloom.bloom_api_activity_types(
                    admin, kind, artefact_id
                )
            self.tc_setup += [
                (created.status_code, self.parameters.STATUS_CREATED),
                (review_setup, self.parameters.REVIEW_SETUP_EXPECTED),
                (reviewed.status_code, self.parameters.STATUS_OK),
                (approved.status_code, self.parameters.STATUS_OK),
            ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    SignOffActivityTest().run()
