"""
* @file     ${tests/sec/docs_facade_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which documents an external reader gets through the project's document pages.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the documents an external reader lists and opens.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocsFacadeExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_customer_documents(self):
        self.print_variables({"status": self.listed.status, "body": self.listed.body})
        self.assertEqual(
            (self.listed.status, sorted(row["doc_id"] for row in self.listed.body["items"])),
            (
                self.parameters.STATUS_OK,
                sorted([self.parameters.READER_CUSTOMER_REQ, self.parameters.READER_CUSTOMER_SPEC]),
            ),
            msg=self.parameters.MSG_READER_DOCS_LIST,
            abort_on_fail=False,
        )

    def bud_listed_documents_carry_the_customer_visibility(self):
        self.assertEqual(
            {row["visibility"] for row in self.listed.body["items"]},
            {self.parameters.CUSTOMER_VISIBILITY},
            msg=self.parameters.MSG_READER_DOCS_VISIBILITY,
            abort_on_fail=False,
        )

    def bud_customer_documents_open_and_internal_ones_are_hidden(self):
        self.print_variables(
            {
                "customer requirement, internal requirement, customer specification, internal specification": self.details
            }
        )
        self.assertEqual(
            self.details,
            self.parameters.READER_DETAIL_STATUSES,
            msg=self.parameters.MSG_READER_DOCS_DETAIL,
            abort_on_fail=False,
        )
