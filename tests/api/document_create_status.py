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
        for doc_type in self.parameters.DOC_STATUS_TYPES:
            created = self._create(
                title=f"{doc_type} from the create page",
                doc_type=doc_type,
                **self.parameters.DOC_STATUS_PAGE_BODY,
            )
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
        plain = self._create(**self.parameters.DOC_STATUS_PLAIN)
        body = plain.body or {}
        self.print_variables({"status": plain.status, "body": body})
        self._equal(
            plain.status,
            self.parameters.STATUS_CREATED,
            self.parameters.MSG_DOC_STATUS_CREATED,
        )
        self._equal(
            body.get("status"),
            self.parameters.DOC_STATUS_DRAFT,
            self.parameters.MSG_DOC_STATUS_DRAFT,
        )

    def bud_other_first_status_is_refused(self):
        for status in self.parameters.DOC_STATUS_REFUSED:
            created = self._create(
                title=f"Specification in {status}",
                doc_type=self.parameters.DOC_STATUS_REFUSED_TYPE,
                status=status,
            )
            answer = self.bloom.bloom_api_call("GET", self.path, self.admin)
            listed = answer.status
            titles = [item.get("title") for item in (answer.body or {}).get("items", [])]
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

    def _create(self, **fields):
        """Create a document in the project with the given fields."""
        return self.bloom.bloom_api_call(
            "POST", self.path, self.admin, json={"project_id": self.project_id, **fields}
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
