"""
* @file     ${tests/api/BLOOM_requirement_workflow_activity.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A requirement logs review, approval and a revision under an approved change.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests one requirement signed off, edited, and revised under a change.
"""

from tests.api.requirement_workflow_activity import RequirementWorkflowActivityBase


class RequirementWorkflowActivityTest(RequirementWorkflowActivityBase):

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
        created = self.bloom.bloom_api_create_artefact(
            admin, self.parameters.REQUIREMENT_KIND, project_id, self.parameters.ARTEFACT_TITLE
        )
        requirement_id = created.json()["id"]
        self.tc_refused = self.bloom.bloom_api_update_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            requirement_id,
            {
                "reviewed_by_id": self.tc_admin_id,
                "reviewed_at": self.parameters.FORGED_REVIEWED_AT,
            },
        )
        review_setup, self.tc_reviewed = self.bloom.bloom_api_review(
            admin, self.parameters.REQUIREMENT_KIND, requirement_id, self.tc_admin_id
        )
        self.tc_reviewed_events = self.bloom.bloom_api_activity_types(
            admin, self.parameters.REQUIREMENT_KIND, requirement_id
        )
        approved = self.bloom.bloom_api_sign_off(
            admin,
            self.parameters.REQUIREMENT_KIND,
            requirement_id,
            self.parameters.APPROVE_STEP,
        )
        self.tc_approved_events = self.bloom.bloom_api_activity_types(
            admin, self.parameters.REQUIREMENT_KIND, requirement_id
        )
        self.tc_status_only = self.bloom.bloom_api_update_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            requirement_id,
            {"status": self.parameters.STATUS_APPROVED},
        ).status_code
        self.tc_status_events = self.bloom.bloom_api_activity_types(
            admin, self.parameters.REQUIREMENT_KIND, requirement_id
        )
        self.tc_mixed = self.bloom.bloom_api_update_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            requirement_id,
            {"title": self.parameters.RENAMED_TITLE, "status": self.parameters.STATUS_DRAFT},
        ).status_code

        change = self.bloom.bloom_api_create_artefact(
            admin, self.parameters.CHANGE_KIND, project_id, self.parameters.ARTEFACT_TITLE
        )
        change_id = change.json()["id"]
        change_setup, reviewed_change = self.bloom.bloom_api_review(
            admin, self.parameters.CHANGE_KIND, change_id, self.tc_admin_id
        )
        approved_change = self.bloom.bloom_api_sign_off(
            admin, self.parameters.CHANGE_KIND, change_id, self.parameters.APPROVE_STEP
        )
        linked = self.bloom.bloom_api_link(admin, project_id, change_id, requirement_id)
        self.tc_edited = self.bloom.bloom_api_update_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            requirement_id,
            {"title": self.parameters.RENAMED_TITLE},
        )
        self.tc_revision_events = self.bloom.bloom_api_activity_types(
            admin, self.parameters.REQUIREMENT_KIND, requirement_id
        )
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (created.status_code, self.parameters.STATUS_CREATED),
            (review_setup, self.parameters.REVIEW_SETUP_EXPECTED),
            (approved.status_code, self.parameters.STATUS_OK),
            (change.status_code, self.parameters.STATUS_CREATED),
            (change_setup, self.parameters.REVIEW_SETUP_EXPECTED),
            (reviewed_change.status_code, self.parameters.STATUS_OK),
            (approved_change.status_code, self.parameters.STATUS_OK),
            (linked.status_code, self.parameters.STATUS_CREATED),
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementWorkflowActivityTest().run()
