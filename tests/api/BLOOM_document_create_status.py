"""
* @file     ${tests/api/BLOOM_document_create_status.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A document is created in Draft; naming another first status answers 422.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the document create route of the full app in-process.
"""

from tests.api.document_create_status import DocumentCreateStatusBase


class DocumentCreateStatusTest(DocumentCreateStatusBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project_id = (
            self.bloom.bloom_api_create_project(admin, self.parameters.DOC_STATUS_PREFIX)
            .json()
            .get("id")
        )
        path = f"/api/projects/{project_id}/documents"

        def create(**fields):
            return self.bloom.bloom_api_call(
                "POST", path, admin, json={"project_id": project_id, **fields}
            )

        self.tc_page = {
            doc_type: create(
                title=f"{doc_type} from the create page",
                doc_type=doc_type,
                **self.parameters.DOC_STATUS_PAGE_BODY,
            )
            for doc_type in self.parameters.DOC_STATUS_TYPES
        }
        self.tc_plain = create(**self.parameters.DOC_STATUS_PLAIN)
        self.tc_refused = {}
        for status in self.parameters.DOC_STATUS_REFUSED:
            created = create(
                title=f"Specification in {status}",
                doc_type=self.parameters.DOC_STATUS_REFUSED_TYPE,
                status=status,
            )
            listed = self.bloom.bloom_api_call("GET", path, admin)
            titles = [item.get("title") for item in (listed.body or {}).get("items", [])]
            self.tc_refused[status] = (created, listed.status, titles)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentCreateStatusTest().run()
