"""
* @file     ${tests/api/links_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the link rules over HTTP.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the link rules over HTTP.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class LinksHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_forbidden_role_is_refused_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.LNK_PREFIXES[0])["id"]
        requirement = self.bloom.bloom_api_create_requirement(
            self.admin, project, "Requirement"
        ).json()["id"]
        test_case = self.bloom.bloom_api_add_test_case(self.admin, project, "Test case").body["id"]
        body = {
            "project_id": project,
            "source_type": "TC",
            "source_id": test_case,
            "target_type": "REQ",
            "target_id": requirement,
            "role": "references",
        }
        answer = self.bloom.bloom_api_call("POST", "/api/links", self.admin, json=body)
        self.print_variables({"answer": answer.body})
        self.assertEqual(
            (answer.status, "not allowed" in answer.body["detail"].lower()),
            (values.STATUS_UNPROCESSABLE, True),
            msg=values.MSG_LNK_FORBIDDEN,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/links",
        )

    def bud_a_legacy_link_is_listed_and_blocks_a_duplicate(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.LNK_PREFIXES[1])["id"]
        concept = self.bloom.bloom_api_call(
            "POST",
            "/api/test-concepts",
            self.admin,
            json={"project_id": project, "name": "Existing concept"},
        ).body["id"]
        test_case = self.bloom.bloom_api_add_test_case(
            self.admin, project, "Existing test case"
        ).body["id"]
        self.bloom.bloom_add_record(
            "ArtefactLink",
            project_id=project,
            source_type="TCO",
            source_id=concept,
            target_type="TC",
            target_id=test_case,
            role="implements",
            suspect=False,
        )
        listed = self.bloom.bloom_api_call(
            "GET",
            "/api/links",
            self.admin,
            params={"project_id": project, "source_type": "CPT", "source_id": concept},
        )
        self.print_variables({"listed": listed.body})
        self.assertEqual(
            (listed.status, [(link["source_type"], link["target_type"]) for link in listed.body]),
            (values.STATUS_OK, [("CPT", "TC")]),
            msg=values.MSG_LNK_LEGACY,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/links",
        )
        body = {
            "project_id": project,
            "source_type": "CPT",
            "source_id": concept,
            "target_type": "TC",
            "target_id": test_case,
            "role": "implements",
        }
        duplicate = self.bloom.bloom_api_call("POST", "/api/links", self.admin, json=body)
        self.assertEqual(
            (duplicate.status, duplicate.body["detail"]),
            (values.STATUS_BAD_REQUEST, "Link already exists"),
            msg=values.MSG_LNK_DUPLICATE,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/links",
        )
