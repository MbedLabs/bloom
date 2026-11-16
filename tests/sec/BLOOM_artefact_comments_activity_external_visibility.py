"""
* @file     ${tests/sec/BLOOM_artefact_comments_activity_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader gets the comments and activity of a customer requirement and a 404 for an internal one.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the comments and activity API with one external reader, one customer and one internal requirement.
"""

from tests.sec.artefact_comments_activity_external_visibility import (
    ArtefactCommentsActivityExternalVisibilityBase,
)


class ArtefactCommentsActivityExternalVisibilityTest(
    ArtefactCommentsActivityExternalVisibilityBase
):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        kind = values.READER_REQUIREMENT_KIND
        reader = bloom.bloom_create_external_reader_environment(
            bloom.bloom_default_external_doc_types()
        )
        customer = bloom.bloom_add_requirement(
            reader.project_id, values.READER_CUSTOMER_REQ, values.CUSTOMER_VISIBILITY
        )
        internal = bloom.bloom_add_requirement(
            reader.project_id, values.READER_INTERNAL_REQ, values.INTERNAL_VISIBILITY
        )
        bloom.bloom_add_comment(kind, customer, values.READER_VISIBLE_COMMENT)
        bloom.bloom_add_comment(kind, internal, values.READER_HIDDEN_COMMENT)
        bloom.bloom_add_activity(kind, customer, values.READER_VISIBLE_ACTIVITY)
        bloom.bloom_add_activity(kind, internal, values.READER_HIDDEN_ACTIVITY)
        self.tc_hidden_comments = bloom.bloom_api_comments(reader.headers, kind, internal)
        self.tc_hidden_activity = bloom.bloom_api_activity(reader.headers, kind, internal)
        self.tc_comments = bloom.bloom_api_comments(reader.headers, kind, customer)
        self.tc_activity = bloom.bloom_api_activity(reader.headers, kind, customer)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ArtefactCommentsActivityExternalVisibilityTest().run()
