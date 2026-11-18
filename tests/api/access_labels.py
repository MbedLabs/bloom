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
        by_number = self.bloom.bloom_api_open_requirement_doc(
            self.admin, self.parameters.LABELS_PREFIX, self.requirement["id"]
        )
        by_doc_id = self.bloom.bloom_api_open_requirement_doc(
            self.admin, self.parameters.LABELS_PREFIX, self.requirement["req_id"]
        )
        found = (
            by_number.status_code,
            by_number.json().get("doc_id"),
            by_number.json().get("id"),
            by_doc_id.json().get("id"),
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
        missing = self.bloom.bloom_api_open_requirement_doc(
            self.admin, self.parameters.LABELS_PREFIX, self.parameters.MISSING_DOC_NUMBER
        )
        self.print_variables({"status": missing.status_code})
        self.assertEqual(
            missing.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_UNKNOWN_ID_NOT_FOUND,
            abort_on_fail=False,
        )

    def bud_member_without_read_gets_not_found(self):
        hidden = self.bloom.bloom_api_open_requirement_doc(
            self.hidden, self.parameters.LABELS_PREFIX, self.requirement["id"]
        )
        self.print_variables({"status": hidden.status_code})
        self.assertEqual(
            hidden.status_code,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_HIDDEN_NOT_FOUND,
            abort_on_fail=False,
        )

    def bud_reader_opens_the_document(self):
        reader = self.bloom.bloom_api_open_requirement_doc(
            self.reader, self.parameters.LABELS_PREFIX, self.requirement["id"]
        )
        found = (reader.status_code, reader.json().get("doc_id"))
        self.print_variables({"reader": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, self.requirement["req_id"]),
            msg=self.parameters.MSG_READER_OPENS,
            abort_on_fail=False,
        )

    def bud_admin_cannot_request_access(self):
        admin_request = self.bloom.bloom_api_request_access(
            self.admin,
            self.parameters.ACCESS_REQUIREMENT,
            self.requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        found = (
            admin_request.status_code,
            admin_request.json().get("detail"),
            len(self.mail),
        )
        self.print_variables({"admin request": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_CONFLICT, self.parameters.ADMIN_REQUEST_DETAIL, 0),
            msg=self.parameters.MSG_ADMIN_CANNOT_REQUEST,
            abort_on_fail=False,
        )

    def bud_holders_cannot_request_their_access(self):
        project_request = self.bloom.bloom_api_request_access(
            self.hidden,
            self.parameters.ACCESS_PROJECT,
            self.parameters.LABELS_PREFIX,
            self.parameters.LABELS_PREFIX,
        )
        item_request = self.bloom.bloom_api_request_access(
            self.reader,
            self.parameters.ACCESS_REQUIREMENT,
            self.requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        found = [
            (project_request.status_code, project_request.json().get("detail")),
            (item_request.status_code, item_request.json().get("detail")),
            len(self.mail),
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
        created = self.bloom.bloom_api_request_access(
            self.hidden,
            self.parameters.ACCESS_DOCUMENT,
            self.requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        mine = self.bloom.bloom_api_my_access_request(
            self.hidden,
            self.parameters.ACCESS_DOCUMENT,
            self.requirement["id"],
            self.parameters.LABELS_PREFIX,
        )
        gone = self.bloom.bloom_api_request_access(
            self.hidden,
            self.parameters.ACCESS_DOCUMENT,
            self.parameters.MISSING_DOC_NUMBER,
            self.parameters.LABELS_PREFIX,
        )
        listed = self.bloom.bloom_api_list_access_requests(
            self.admin, self.parameters.LABELS_PREFIX
        )
        labels = {row["id"]: row["resource_label"] for row in listed.json()}
        found = (
            created.status_code,
            created.json().get("resource_label"),
            mine.json().get("resource_label"),
            gone.status_code,
            labels.get(created.json().get("id")),
            labels.get(gone.json().get("id")),
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
        self.bloom.bloom_api_get_requirement(self.admin, self.requirement["id"])
        self.bloom.bloom_api_get_user(self.admin, self.hidden_user["id"])
        self.bloom.bloom_api_get_requirement(self.admin, self.parameters.MISSING_REQUIREMENT_NUMBER)
        requirement = self.bloom.bloom_api_audit_event(
            self.admin,
            self.parameters.AUDIT_REQUEST_ACTION,
            self.parameters.ACCESS_REQUIREMENT,
            self.requirement["id"],
        )
        user = self.bloom.bloom_api_audit_event(
            self.admin,
            self.parameters.AUDIT_REQUEST_ACTION,
            self.parameters.AUDIT_USER_TARGET,
            self.hidden_user["id"],
        )
        deleted = self.bloom.bloom_api_audit_event(
            self.admin,
            self.parameters.AUDIT_REQUEST_ACTION,
            self.parameters.ACCESS_REQUIREMENT,
            self.parameters.MISSING_REQUIREMENT_NUMBER,
        )
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
