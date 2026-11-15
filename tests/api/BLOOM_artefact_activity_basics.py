"""
* @file     ${tests/api/BLOOM_artefact_activity_basics.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The REQ docs list gives type and origin; creating and editing log their activity.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests a typed requirement, an edited requirement and a new document.
"""

from tests.api.artefact_activity_basics import ArtefactActivityBasicsBase


class ArtefactActivityBasicsTest(ArtefactActivityBasicsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(admin, self.parameters.ACTIVITY_PREFIX)
        project_id = project.json()["id"]
        typed = self.bloom.bloom_api_create_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            project_id,
            self.parameters.ARTEFACT_TITLE,
            req_type=self.parameters.REQ_TYPE,
            req_origin=self.parameters.REQ_ORIGIN,
        )
        listed = self.bloom.bloom_api_list_docs(
            admin, self.parameters.ACTIVITY_PREFIX, self.parameters.DOCS_TYPE_FILTER
        )
        self.tc_docs_row = next(
            (
                row
                for row in listed.json().get("items", [])
                if row["doc_type"] == self.parameters.DOCS_TYPE_FILTER
                and row["title"] == self.parameters.ARTEFACT_TITLE
            ),
            None,
        )
        document = self.bloom.bloom_api_create_artefact(
            admin, self.parameters.DOCUMENT_KIND, project_id, self.parameters.ARTEFACT_TITLE
        )
        self.tc_created_events = {
            self.parameters.REQUIREMENT_KIND: self.bloom.bloom_api_activity_types(
                admin, self.parameters.REQUIREMENT_KIND, typed.json()["id"]
            ),
            self.parameters.DOCUMENT_KIND: self.bloom.bloom_api_activity_types(
                admin, self.parameters.DOCUMENT_KIND, document.json()["id"]
            ),
        }
        updated = self.bloom.bloom_api_update_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            typed.json()["id"],
            {"title": self.parameters.RENAMED_TITLE},
        )
        self.tc_updated_events = self.bloom.bloom_api_activity_types(
            admin, self.parameters.REQUIREMENT_KIND, typed.json()["id"]
        )
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (typed.status_code, self.parameters.STATUS_CREATED),
            (listed.status_code, self.parameters.STATUS_OK),
            (document.status_code, self.parameters.STATUS_CREATED),
            (updated.status_code, self.parameters.STATUS_OK),
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactActivityBasicsTest().run()
