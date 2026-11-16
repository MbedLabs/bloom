"""
* @file     ${tests/api/access_labels.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests numeric document addresses, access requests and target labels.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the document addresses and labels.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class AccessLabelsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.setup})
        self.assertEqual(
            [found for found, _ in self.setup],
            [expected for _, expected in self.setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_database_id_opens_the_document(self):
        found = (
            self.by_number.status_code,
            self.by_number.json().get("doc_id"),
            self.by_number.json().get("id"),
            self.by_doc_id.json().get("id"),
        )
        self.print_variables({"status, doc id, id, id by doc id": found})
        self.assertEqual(
            found,
            (
                self.parameters.STATUS_OK,
                self.requirement["req_id"],
                self.requirement["id"],
                self.requirement["id"],
            ),
            msg=self.parameters.MSG_ID_OPENS_DOCUMENT,
            abort_on_fail=False,
        )

    def bud_unknown_id_is_not_found(self):
        self.print_variables({"status": self.missing.status_code})
        self.assertEqual(
            self.missing.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_UNKNOWN_ID_NOT_FOUND,
            abort_on_fail=False,
        )

    def bud_member_without_read_gets_not_found(self):
        self.print_variables({"status": self.hidden.status_code})
        self.assertEqual(
            self.hidden.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_HIDDEN_NOT_FOUND,
            abort_on_fail=False,
        )

    def bud_reader_opens_the_document(self):
        found = (self.reader.status_code, self.reader.json().get("doc_id"))
        self.print_variables({"reader": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.requirement["req_id"]),
            msg=self.parameters.MSG_READER_OPENS,
            abort_on_fail=False,
        )

    def bud_admin_cannot_request_access(self):
        found = (
            self.admin_request.status_code,
            self.admin_request.json().get("detail"),
            self.mail_after_admin,
        )
        self.print_variables({"admin request": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_CONFLICT, self.parameters.ADMIN_REQUEST_DETAIL, 0),
            msg=self.parameters.MSG_ADMIN_CANNOT_REQUEST,
            abort_on_fail=False,
        )

    def bud_holders_cannot_request_their_access(self):
        found = [
            (self.project_request.status_code, self.project_request.json().get("detail")),
            (self.item_request.status_code, self.item_request.json().get("detail")),
            self.mail_after_holders,
        ]
        self.print_variables({"holder requests": found})
        self.assertEqual(
            found,
            [
                (
                    self.parameters.STATUS_CONFLICT,
                    self.parameters.ALREADY_HAVE_ACCESS.format(
                        target=self.parameters.LABELS_PREFIX
                    ),
                ),
                (
                    self.parameters.STATUS_CONFLICT,
                    self.parameters.ALREADY_HAVE_ACCESS.format(target=self.requirement["req_id"]),
                ),
                0,
            ],
            msg=self.parameters.MSG_HOLDER_CANNOT_REQUEST,
            abort_on_fail=False,
        )

    def bud_requests_name_the_document_for_admins_only(self):
        labels = {row["id"]: row["resource_label"] for row in self.listed.json()}
        found = (
            self.created.status_code,
            self.created.json().get("resource_label"),
            self.mine.json().get("resource_label"),
            self.gone.status_code,
            labels.get(self.created.json().get("id")),
            labels.get(self.gone.json().get("id")),
        )
        self.print_variables({"labels": found})
        self.assertEqual(
            found,
            (
                self.parameters.STATUS_CREATED,
                str(self.requirement["id"]),
                str(self.requirement["id"]),
                self.parameters.STATUS_CREATED,
                self.requirement["req_id"],
                self.parameters.DELETED_LABEL.format(ref=self.parameters.MISSING_DOC_NUMBER),
            ),
            msg=self.parameters.MSG_REQUEST_LABELS,
            abort_on_fail=False,
        )

    def bud_request_mail_goes_to_others(self):
        recipients = {mail["to_email"] for mail in self.mail}
        found = (
            self.parameters.HIDDEN_EMAIL in recipients,
            bool(recipients),
            self.mail[0].get("resource") if self.mail else None,
        )
        self.print_variables({"recipients": sorted(recipients), "found": found})
        self.assertEqual(
            found,
            (False, True, self.requirement["req_id"]),
            msg=self.parameters.MSG_REQUEST_MAIL,
            abort_on_fail=False,
        )

    def bud_audit_log_names_targets_and_actors(self):
        requirement, user, deleted = self.audit
        found = (
            (requirement or {}).get("target_label"),
            (requirement or {}).get("actor_label") == (requirement or {}).get("actor_name"),
            (user or {}).get("target_label"),
            (deleted or {}).get("target_label"),
        )
        self.print_variables({"audit labels": found})
        self.assertEqual(
            found,
            (
                self.parameters.AUDIT_REQUIREMENT_LABEL.format(ref=self.requirement["req_id"]),
                True,
                self.parameters.AUDIT_USER_LABEL.format(name=self.parameters.MEMBER_FULL_NAME),
                self.parameters.AUDIT_REQUIREMENT_LABEL.format(
                    ref=self.parameters.DELETED_LABEL.format(
                        ref=self.parameters.MISSING_REQUIREMENT_NUMBER
                    )
                ),
            ),
            msg=self.parameters.MSG_AUDIT_LABELS,
            abort_on_fail=False,
        )
