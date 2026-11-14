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
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_database_id_opens_the_document(self):
        found = (
            self.tc_by_number.status_code,
            self.tc_by_number.json().get("doc_id"),
            self.tc_by_number.json().get("id"),
            self.tc_by_doc_id.json().get("id"),
        )
        self.print_variables({"status, doc id, id, id by doc id": found})
        self.assertEqual(
            found,
            (
                self.parameters.STATUS_OK,
                self.tc_requirement["req_id"],
                self.tc_requirement["id"],
                self.tc_requirement["id"],
            ),
            msg=self.parameters.MSG_ID_OPENS_DOCUMENT,
            abort_on_fail=False,
        )

    def bud_unknown_id_is_not_found(self):
        self.print_variables({"status": self.tc_missing.status_code})
        self.assertEqual(
            self.tc_missing.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_UNKNOWN_ID_NOT_FOUND,
            abort_on_fail=False,
        )

    def bud_member_without_read_gets_not_found(self):
        self.print_variables({"status": self.tc_hidden.status_code})
        self.assertEqual(
            self.tc_hidden.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_HIDDEN_NOT_FOUND,
            abort_on_fail=False,
        )

    def bud_reader_opens_the_document(self):
        found = (self.tc_reader.status_code, self.tc_reader.json().get("doc_id"))
        self.print_variables({"reader": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.tc_requirement["req_id"]),
            msg=self.parameters.MSG_READER_OPENS,
            abort_on_fail=False,
        )

    def bud_admin_cannot_request_access(self):
        found = (
            self.tc_admin_request.status_code,
            self.tc_admin_request.json().get("detail"),
            self.tc_mail_after_admin,
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
            (self.tc_project_request.status_code, self.tc_project_request.json().get("detail")),
            (self.tc_item_request.status_code, self.tc_item_request.json().get("detail")),
            self.tc_mail_after_holders,
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
                    self.parameters.ALREADY_HAVE_ACCESS.format(
                        target=self.tc_requirement["req_id"]
                    ),
                ),
                0,
            ],
            msg=self.parameters.MSG_HOLDER_CANNOT_REQUEST,
            abort_on_fail=False,
        )

    def bud_requests_name_the_document_for_admins_only(self):
        labels = {row["id"]: row["resource_label"] for row in self.tc_listed.json()}
        found = (
            self.tc_created.status_code,
            self.tc_created.json().get("resource_label"),
            self.tc_mine.json().get("resource_label"),
            self.tc_gone.status_code,
            labels.get(self.tc_created.json().get("id")),
            labels.get(self.tc_gone.json().get("id")),
        )
        self.print_variables({"labels": found})
        self.assertEqual(
            found,
            (
                self.parameters.STATUS_CREATED,
                str(self.tc_requirement["id"]),
                str(self.tc_requirement["id"]),
                self.parameters.STATUS_CREATED,
                self.tc_requirement["req_id"],
                self.parameters.DELETED_LABEL.format(ref=self.parameters.MISSING_DOC_NUMBER),
            ),
            msg=self.parameters.MSG_REQUEST_LABELS,
            abort_on_fail=False,
        )

    def bud_request_mail_goes_to_others(self):
        recipients = {mail["to_email"] for mail in self.tc_mail}
        found = (
            self.parameters.HIDDEN_EMAIL in recipients,
            bool(recipients),
            self.tc_mail[0].get("resource") if self.tc_mail else None,
        )
        self.print_variables({"recipients": sorted(recipients), "found": found})
        self.assertEqual(
            found,
            (False, True, self.tc_requirement["req_id"]),
            msg=self.parameters.MSG_REQUEST_MAIL,
            abort_on_fail=False,
        )

    def bud_audit_log_names_targets_and_actors(self):
        requirement, user, deleted = self.tc_audit
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
                self.parameters.AUDIT_REQUIREMENT_LABEL.format(ref=self.tc_requirement["req_id"]),
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
