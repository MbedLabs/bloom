"""
* @file     ${tests/api/tag_links_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a tag in a document body becomes a references link.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the tag links over HTTP.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TagLinksHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_tag_creates_a_references_link(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[0])["id"]
        target = self.bloom.bloom_api_add_to(self.admin, project, "SPEC", "Target").body["id"]
        source = self.bloom.bloom_api_add_to(
            self.admin,
            project,
            "REQ",
            "Source",
            content_json=self.bloom.bloom_tag_body("SPEC", target),
        ).body["id"]
        self.assertEqual(
            self.bloom.bloom_api_links(self.admin, project, source_type="REQ", source_id=source),
            [("SPEC", target, "references")],
            msg=values.MSG_TGL_CREATED,
            abort_on_fail=False,
        )

    def bud_the_tag_is_read_as_a_backlink(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[1])["id"]
        target = self.bloom.bloom_api_add_to(self.admin, project, "SPEC", "Target").body["id"]
        self.bloom.bloom_api_add_to(
            self.admin,
            project,
            "REQ",
            "Source",
            content_json=self.bloom.bloom_tag_body("SPEC", target),
        )
        incoming = self.bloom.bloom_api_links(
            self.admin, project, target_type="SPEC", target_id=target
        )
        self.assertEqual(
            [role for _, _, role in incoming],
            ["references"],
            msg=values.MSG_TGL_BACKLINK,
            abort_on_fail=False,
        )

    def bud_the_same_tag_twice_is_one_link(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[2])["id"]
        target = self.bloom.bloom_api_add_to(self.admin, project, "SPEC", "Target").body["id"]
        body = self.bloom.bloom_tag_body("SPEC", target)
        source = self.bloom.bloom_api_add_to(
            self.admin, project, "REQ", "Source", content_json=body
        ).body["id"]
        updated = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{source}", self.admin, json={"content_json": body}
        )
        self.assertEqual(
            (
                updated.status,
                len(
                    self.bloom.bloom_api_links(
                        self.admin, project, source_type="REQ", source_id=source
                    )
                ),
            ),
            (values.STATUS_OK, 1),
            msg=values.MSG_TGL_ONCE,
            abort_on_fail=False,
        )

    def bud_a_document_tagging_itself_creates_nothing(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[3])["id"]
        source = self.bloom.bloom_api_add_to(self.admin, project, "REQ", "Source").body["id"]
        updated = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/requirements/{source}",
            self.admin,
            json={"content_json": self.bloom.bloom_tag_body("REQ", source)},
        )
        self.assertEqual(
            (
                updated.status,
                self.bloom.bloom_api_links(
                    self.admin, project, source_type="REQ", source_id=source
                ),
            ),
            (values.STATUS_OK, []),
            msg=values.MSG_TGL_SELF,
            abort_on_fail=False,
        )

    def bud_a_tag_of_an_unknown_type_is_refused_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[4])["id"]
        refused = self.bloom.bloom_api_add_to(
            self.admin, project, "REQ", "Source", content_json=self.bloom.bloom_tag_body("NOPE", 1)
        )
        requirements = self.bloom.bloom_api_call(
            "GET", "/api/requirements", self.admin, params={"project_id": project}
        ).body["items"]
        self.print_variables({"refused": refused.body})
        self.assertEqual(
            (
                refused.status,
                "NOPE" in refused.body["detail"],
                self.bloom.bloom_api_links(self.admin, project),
                requirements,
            ),
            (values.STATUS_UNPROCESSABLE, True, [], []),
            msg=values.MSG_TGL_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_a_parameter_mention_is_not_a_tag(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[5])["id"]
        source = self.bloom.bloom_api_add_to(
            self.admin, project, "REQ", "Source", content_json=values.TGL_PARAMETER_BODY
        ).body["id"]
        self.assertEqual(
            self.bloom.bloom_api_links(self.admin, project, source_type="REQ", source_id=source),
            [],
            msg=values.MSG_TGL_PARAMETER,
            abort_on_fail=False,
        )

    def bud_a_specification_can_tag_a_requirement(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[6])["id"]
        target = self.bloom.bloom_api_add_to(self.admin, project, "REQ", "Target").body["id"]
        source = self.bloom.bloom_api_add_to(
            self.admin,
            project,
            "SPEC",
            "Source",
            content_json=self.bloom.bloom_tag_body("REQ", target),
        )
        self.assertEqual(
            (
                source.status in (values.STATUS_OK, values.STATUS_CREATED),
                self.bloom.bloom_api_links(
                    self.admin, project, source_type="SPEC", source_id=source.body["id"]
                ),
            ),
            (True, [("REQ", target, "references")]),
            msg=values.MSG_TGL_PAIR.format(source="specification", target="requirement"),
            abort_on_fail=False,
        )

    def bud_a_requirement_can_tag_a_requirement(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[7])["id"]
        target = self.bloom.bloom_api_add_to(self.admin, project, "REQ", "Target").body["id"]
        source = self.bloom.bloom_api_add_to(
            self.admin,
            project,
            "REQ",
            "Source",
            content_json=self.bloom.bloom_tag_body("REQ", target),
        )
        self.assertEqual(
            (
                source.status in (values.STATUS_OK, values.STATUS_CREATED),
                self.bloom.bloom_api_links(
                    self.admin, project, source_type="REQ", source_id=source.body["id"]
                ),
            ),
            (True, [("REQ", target, "references")]),
            msg=values.MSG_TGL_PAIR.format(source="requirement", target="requirement"),
            abort_on_fail=False,
        )

    def bud_a_requirement_can_tag_a_design(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[8])["id"]
        target = self.bloom.bloom_api_add_to(self.admin, project, "DES", "Target").body["id"]
        source = self.bloom.bloom_api_add_to(
            self.admin,
            project,
            "REQ",
            "Source",
            content_json=self.bloom.bloom_tag_body("DES", target),
        )
        self.assertEqual(
            (
                source.status in (values.STATUS_OK, values.STATUS_CREATED),
                self.bloom.bloom_api_links(
                    self.admin, project, source_type="REQ", source_id=source.body["id"]
                ),
            ),
            (True, [("DES", target, "references")]),
            msg=values.MSG_TGL_PAIR.format(source="requirement", target="design"),
            abort_on_fail=False,
        )

    def bud_a_test_case_body_hosts_no_tags(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TGL_PREFIXES[9])["id"]
        requirement = self.bloom.bloom_api_add_to(self.admin, project, "REQ", "Requirement").body[
            "id"
        ]
        case = self.bloom.bloom_api_add_to(
            self.admin,
            project,
            "TC",
            "Case",
            content_json=self.bloom.bloom_tag_body("REQ", requirement),
        )
        self.assertEqual(
            (
                case.status in (values.STATUS_OK, values.STATUS_CREATED),
                self.bloom.bloom_api_links(
                    self.admin, project, source_type="TC", source_id=case.body["id"]
                ),
            ),
            (True, []),
            msg=values.MSG_TGL_TEST_CASE,
            abort_on_fail=False,
        )
