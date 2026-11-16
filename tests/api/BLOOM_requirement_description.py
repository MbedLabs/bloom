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

TEXT_FIELDS = ("description", "content_json", "content_html")


class RequirementDescriptionTest(RequirementDescriptionBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        parameters = self.parameters
        bloom.bloom_start_full_api()
        bloom.bloom_add_admin(parameters.API_ADMIN_EMAIL, parameters.API_PASSWORD)
        admin, _ = bloom.bloom_log_in(parameters.API_ADMIN_EMAIL, parameters.API_PASSWORD)
        project_id = (
            bloom.bloom_api_create_project(admin, parameters.DESCRIPTION_PREFIX).json().get("id")
        )
        spec = bloom.bloom_api_create_artefact(
            admin, parameters.DOCUMENT_KIND, project_id, parameters.DESCRIPTION_SPEC_TITLE
        ).json()
        self.expected_link = (
            parameters.DESCRIPTION_TAG_TYPE,
            spec.get("id"),
            parameters.DESCRIPTION_TAG_ROLE,
        )
        path = parameters.ARTEFACT_PATHS[parameters.REQUIREMENT_KIND]

        def create(title, **fields):
            return bloom.bloom_api_call(
                "POST", path, admin, json={"project_id": project_id, "title": title, **fields}
            )

        def text_of(body):
            return tuple((body or {}).get(name) for name in TEXT_FIELDS)

        def links_of(requirement):
            listed = bloom.bloom_api_call(
                "GET",
                "/api/links",
                admin,
                params={
                    "project_id": project_id,
                    "source_type": "REQ",
                    "source_id": (requirement.body or {}).get("id"),
                },
            )
            return [
                (link["target_type"], link["target_id"], link["role"]) for link in listed.body or []
            ]

        from_body = create(
            "Boot budget",
            content_json=parameters.DESCRIPTION_BODY,
            content_html=parameters.DESCRIPTION_BODY_HTML,
        )
        requirement_path = f"{path}/{from_body.body.get('id')}"
        self.from_body = text_of(from_body.body)
        self.detail = text_of(bloom.bloom_api_call("GET", requirement_path, admin).body)
        edited = bloom.bloom_api_call(
            "PATCH",
            requirement_path,
            admin,
            json={"content_html": parameters.DESCRIPTION_EDIT_HTML},
        )
        self.edited = (edited.status, *text_of(edited.body))

        tagged = create(
            "Tagged",
            description=f"Follows #{spec.get('doc_id')} and {parameters.DESCRIPTION_UNKNOWN_TAG}.",
        )
        self.tagged_links = links_of(tagged)

        untagged = create("Untagged", description=parameters.DESCRIPTION_UNTAGGED)
        self.untagged_links = links_of(untagged)
        retagged = bloom.bloom_api_call(
            "PATCH",
            f"{path}/{untagged.body.get('id')}",
            admin,
            json={"description": f"Now follows #{spec.get('doc_id')}."},
        )
        self.retagged_links = (retagged.status, links_of(untagged))
        self.created = [from_body, tagged, untagged]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RequirementDescriptionTest().run()
