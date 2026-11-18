"""
* @file     ${tests/api/docs_facade_lookups.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the lookups of the document registry by document ID.
* @author   Amine El Omari
* @date     2026-11-17
* @version  1.0.0
* @note     Base class containing the bud methods of the document registry lookups.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocsFacadeLookupsBase(BloomTestCase):

    interface = BloomApiInterface

    def _related(self, doc_id):
        answer = self.bloom.bloom_api_registry(
            self.admin, self.project["prefix"], related_to=doc_id
        )
        items = answer.body.get("items", []) if isinstance(answer.body, dict) else []
        return answer.status, sorted(item["doc_id"] for item in items)

    def bud_the_requirement_is_linked_to_both_documents(self):
        values = self.parameters
        self.print_variables({"link statuses": self.link_statuses})
        self.assertEqual(
            self.link_statuses,
            [values.STATUS_CREATED, values.STATUS_CREATED],
            msg=values.MSG_LKP_LINKS,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/links",
        )

    def bud_related_to_a_specification_lists_its_requirement(self):
        values = self.parameters
        found = self._related(self.specification["doc_id"])
        self.print_variables({"related_to": self.specification["doc_id"], "status, doc_ids": found})
        self.assertEqual(
            found,
            (values.STATUS_OK, [self.requirement["req_id"]]),
            msg=values.MSG_LKP_RELATED_SPEC,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs",
        )

    def bud_related_to_a_standard_lists_its_requirement(self):
        values = self.parameters
        found = self._related(self.standard["doc_id"])
        self.print_variables({"related_to": self.standard["doc_id"], "status, doc_ids": found})
        self.assertEqual(
            found,
            (values.STATUS_OK, [self.requirement["req_id"]]),
            msg=values.MSG_LKP_RELATED_STD,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs",
        )

    def bud_related_to_a_requirement_still_lists_its_documents(self):
        values = self.parameters
        found = self._related(self.requirement["req_id"])
        self.print_variables({"related_to": self.requirement["req_id"], "status, doc_ids": found})
        self.assertEqual(
            found,
            (values.STATUS_OK, sorted([self.specification["doc_id"], self.standard["doc_id"]])),
            msg=values.MSG_LKP_RELATED_REQ,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs",
        )

    def bud_related_to_a_missing_document_is_404(self):
        values = self.parameters
        status, _ = self._related(values.LKP_MISSING_SPEC)
        self.print_variables({"related_to": values.LKP_MISSING_SPEC, "status": status})
        self.assertEqual(
            status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_LKP_RELATED_MISSING,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs",
        )

    def bud_the_requirement_detail_carries_type_and_origin(self):
        values = self.parameters
        answer = self.bloom.bloom_api_open_doc(
            self.admin,
            self.project["prefix"],
            values.LKP_REQUIREMENT_SLUG,
            self.requirement["req_id"],
        )
        found = (answer.status, answer.body.get("req_type"), answer.body.get("req_origin"))
        self.print_variables({"status, req_type, req_origin": found})
        self.assertEqual(
            found,
            (
                values.STATUS_OK,
                values.LKP_REQUIREMENT["req_type"],
                values.LKP_REQUIREMENT["req_origin"],
            ),
            msg=values.MSG_LKP_DETAIL_TYPE,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs/requirements/{doc_id}",
        )

    def bud_a_document_id_is_found_in_lower_case(self):
        values = self.parameters
        reference = self.requirement["req_id"].lower()
        answer = self.bloom.bloom_api_open_doc(
            self.admin, self.project["prefix"], values.LKP_REQUIREMENT_SLUG, reference
        )
        found = (answer.status, answer.body.get("doc_id"))
        self.print_variables({"reference": reference, "status, doc_id": found})
        self.assertEqual(
            found,
            (values.STATUS_OK, self.requirement["req_id"]),
            msg=values.MSG_LKP_ANY_CASE,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects/{prefix}/docs/requirements/{doc_id}",
        )
