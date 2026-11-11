"""
* @file     ${tests/api/document_create_status.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the first status a created document may have.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the document create status.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DocumentCreateStatusBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_create_page_body_creates_a_draft(self):
        for doc_type, created in self.tc_page.items():
            body = created.body or {}
            self.print_variables({"kind": doc_type, "status": created.status, "body": body})
            self._equal(
                created.status,
                self.parameters.STATUS_CREATED,
                self.parameters.MSG_DOC_STATUS_CREATED,
            )
            self._equal(body.get("doc_type"), doc_type, self.parameters.MSG_DOC_STATUS_TYPE)
            self._equal(
                body.get("status"),
                self.parameters.DOC_STATUS_DRAFT,
                self.parameters.MSG_DOC_STATUS_DRAFT,
            )

    def bud_create_without_status_is_a_draft(self):
        body = self.tc_plain.body or {}
        self.print_variables({"status": self.tc_plain.status, "body": body})
        self._equal(
            self.tc_plain.status,
            self.parameters.STATUS_CREATED,
            self.parameters.MSG_DOC_STATUS_CREATED,
        )
        self._equal(
            body.get("status"),
            self.parameters.DOC_STATUS_DRAFT,
            self.parameters.MSG_DOC_STATUS_DRAFT,
        )

    def bud_other_first_status_is_refused(self):
        for status, (created, listed, titles) in self.tc_refused.items():
            detail = (created.body or {}).get("detail") or [{}]
            location = detail[0].get("loc") if isinstance(detail, list) else None
            self.print_variables(
                {"status": status, "answer": created.status, "loc": location, "list": listed}
            )
            self._equal(
                created.status,
                self.parameters.STATUS_UNPROCESSABLE,
                self.parameters.MSG_DOC_STATUS_REFUSED,
            )
            self._equal(
                location, self.parameters.DOC_STATUS_FIELD, self.parameters.MSG_DOC_STATUS_FIELD
            )
            self._equal(listed, self.parameters.STATUS_OK, self.parameters.MSG_DOC_STATUS_LISTED)
            self.assertNotIn(
                f"Specification in {status}",
                titles,
                msg=self.parameters.MSG_DOC_STATUS_NOTHING,
                abort_on_fail=False,
            )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
