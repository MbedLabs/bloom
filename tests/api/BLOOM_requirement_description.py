"""
* @file     ${tests/api/BLOOM_requirement_description.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A requirement stores no editor content and a #ID in its description links that document.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     This module tests the requirements routes of the full app in-process.
"""

from tests.api.requirement_description import RequirementDescriptionBase


class RequirementDescriptionTest(RequirementDescriptionBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        parameters = self.parameters
        bloom.bloom_start_full_api()
        bloom.bloom_add_admin(parameters.API_ADMIN_EMAIL, parameters.API_PASSWORD)
        self.admin, _ = bloom.bloom_log_in(parameters.API_ADMIN_EMAIL, parameters.API_PASSWORD)
        self.project_id = (
            bloom.bloom_api_create_project(self.admin, parameters.DESCRIPTION_PREFIX)
            .json()
            .get("id")
        )
        self.spec = bloom.bloom_api_create_artefact(
            self.admin, parameters.DOCUMENT_KIND, self.project_id, parameters.DESCRIPTION_SPEC_TITLE
        ).json()
        self.expected_link = (
            parameters.DESCRIPTION_TAG_TYPE,
            self.spec.get("id"),
            parameters.DESCRIPTION_TAG_ROLE,
        )
        path = parameters.ARTEFACT_PATHS[parameters.REQUIREMENT_KIND]

        def create(title, **fields):
            return bloom.bloom_api_call(
                "POST",
                path,
                self.admin,
                json={"project_id": self.project_id, "title": title, **fields},
            )

        self.from_body = create(
            "Boot budget",
            content_json=parameters.DESCRIPTION_BODY,
            content_html=parameters.DESCRIPTION_BODY_HTML,
        )
        self.tagged = create(
            "Tagged",
            description=f"Follows #{self.spec.get('doc_id')} and {parameters.DESCRIPTION_UNKNOWN_TAG}.",
        )
        self.untagged = create("Untagged", description=parameters.DESCRIPTION_UNTAGGED)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementDescriptionTest().run()
