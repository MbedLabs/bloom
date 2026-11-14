"""
* @file     ${tests/api/documents_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which documents an external project member sees.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the external document visibility.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocumentsExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_member_signs_in(self):
        self.print_variables({"sign-in": self.tc_sign_in})
        self.assertEqual(
            self.tc_sign_in,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_EXTERNAL_SIGNS_IN,
            abort_on_fail=True,
        )

    def bud_list_holds_the_customer_document_only(self):
        doc_ids = {item["doc_id"] for item in self.tc_listed.json().get("items", [])}
        found = (
            self.tc_listed.status_code,
            self.parameters.CUSTOMER_DOC_ID in doc_ids,
            self.parameters.INTERNAL_DOC_ID in doc_ids,
        )
        self.print_variables({"listed": sorted(doc_ids), "status, customer, internal": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, True, False),
            msg=self.parameters.MSG_EXTERNAL_LIST,
            abort_on_fail=False,
        )

    def bud_internal_document_is_not_found(self):
        self.print_variables({"status": self.tc_internal.status_code})
        self.assertEqual(
            self.tc_internal.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_EXTERNAL_DETAIL,
            abort_on_fail=False,
        )
