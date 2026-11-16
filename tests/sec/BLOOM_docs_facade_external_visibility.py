"""
* @file     ${tests/sec/BLOOM_docs_facade_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader lists and opens customer documents only.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the document pages API with one external reader, two requirements and two specifications.
"""

from tests.sec.docs_facade_external_visibility import DocsFacadeExternalVisibilityBase


class DocsFacadeExternalVisibilityTest(DocsFacadeExternalVisibilityBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment(values.READER_DOC_TYPES)
        project, prefix = reader.project_id, values.VISIBILITY_PREFIX
        customer, internal = values.CUSTOMER_VISIBILITY, values.INTERNAL_VISIBILITY
        bloom.bloom_add_requirement(project, values.READER_CUSTOMER_REQ, customer)
        bloom.bloom_add_requirement(project, values.READER_INTERNAL_REQ, internal)
        bloom.bloom_add_document(
            project, values.READER_CUSTOMER_SPEC, values.READER_CUSTOMER_SPEC, customer
        )
        bloom.bloom_add_document(
            project, values.READER_INTERNAL_SPEC, values.READER_INTERNAL_SPEC, internal
        )
        self.listed = bloom.bloom_api_list_docs_of_types(
            reader.headers, prefix, values.READER_DOC_TYPES
        )
        opened = (
            (values.READER_REQUIREMENTS_SLUG, values.READER_CUSTOMER_REQ),
            (values.READER_REQUIREMENTS_SLUG, values.READER_INTERNAL_REQ),
            (values.READER_SPECIFICATIONS_SLUG, values.READER_CUSTOMER_SPEC),
            (values.READER_SPECIFICATIONS_SLUG, values.READER_INTERNAL_SPEC),
        )
        self.details = tuple(
            bloom.bloom_api_open_doc(reader.headers, prefix, slug, doc_id).status
            for slug, doc_id in opened
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocsFacadeExternalVisibilityTest().run()
