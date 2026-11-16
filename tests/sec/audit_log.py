"""
* @file     ${tests/sec/audit_log.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what the audit log records and who reads it.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the audit log.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class AuditLogBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_wrong_password_is_refused_401(self):
        self.assertEqual(
            self.tc_refused_login.status_code,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_AUDITLOG_REFUSED_LOGIN,
            abort_on_fail=False,
        )

    def bud_refused_sign_in_is_recorded_as_a_failure(self):
        event = self.tc_failed_event
        self.print_variables(
            {
                "outcome": event.outcome,
                "actor": event.actor_type,
                "target": (event.target_type, event.target_id),
            }
        )
        self.assertEqual(
            (event.outcome, event.actor_type, event.target_type, event.target_id),
            (*self.parameters.AUDITLOG_FAILED_LOGIN, str(self.tc_someone)),
            msg=self.parameters.MSG_AUDITLOG_FAILURE,
            abort_on_fail=False,
        )

    def bud_record_carries_the_request_id_the_user_agent_and_an_address(self):
        event = self.tc_failed_event
        self.print_variables(
            {"request": event.request_id, "agent": event.user_agent, "address": event.ip}
        )
        self.assertEqual(
            (event.request_id, event.user_agent, bool(event.ip)),
            (
                self.tc_refused_login.headers["x-request-id"],
                self.parameters.AUDITLOG_USER_AGENT,
                True,
            ),
            msg=self.parameters.MSG_AUDITLOG_REQUEST,
            abort_on_fail=False,
        )

    def bud_record_does_not_contain_the_password_tried(self):
        self.assertNotIn(
            self.parameters.HTTP_WRONG_PASSWORD,
            repr(self.tc_failed_event.details),
            msg=self.parameters.MSG_AUDITLOG_NO_PASSWORD,
            abort_on_fail=False,
        )

    def bud_sign_in_is_recorded_as_a_success_by_the_user(self):
        event = self.tc_login_event
        self.assertEqual(
            (event.outcome, event.actor_type, event.actor_user_id),
            ("success", "user", self.tc_member),
            msg=self.parameters.MSG_AUDITLOG_SUCCESS,
            abort_on_fail=False,
        )

    def bud_role_change_is_recorded_with_both_roles(self):
        event = self.tc_role_event
        self.print_variables({"details": event.details})
        self.assertEqual(
            (self.tc_role_change.status, event.actor_user_id, event.target_id, event.details),
            (
                self.parameters.STATUS_OK,
                self.tc_admin,
                str(self.tc_demoted),
                self.parameters.AUDITLOG_ROLE_CHANGE,
            ),
            msg=self.parameters.MSG_AUDITLOG_ROLE,
            abort_on_fail=False,
        )

    def bud_member_visibility_and_deletion_are_answered(self):
        self.print_variables({"added, changed, deleted": self.tc_statuses})
        self.assertEqual(
            self.tc_statuses,
            (
                self.parameters.STATUS_CREATED,
                self.parameters.STATUS_OK,
                self.parameters.STATUS_NO_CONTENT,
            ),
            msg=self.parameters.MSG_AUDITLOG_STATUSES,
            abort_on_fail=False,
        )

    def bud_added_member_is_recorded_with_the_project(self):
        event = self.tc_member_event
        self.assertEqual(
            (event.project_id, event.target_id),
            (self.tc_project, str(self.tc_member)),
            msg=self.parameters.MSG_AUDITLOG_MEMBER,
            abort_on_fail=False,
        )

    def bud_visibility_change_is_recorded_with_the_new_visibility(self):
        event = self.tc_visibility_event
        self.assertEqual(
            (event.target_id, event.details["to"]),
            (self.parameters.AUDITLOG_DESIGN, self.parameters.CUSTOMER_VISIBILITY),
            msg=self.parameters.MSG_AUDITLOG_VISIBILITY,
            abort_on_fail=False,
        )

    def bud_deletion_is_recorded_with_the_project_and_the_type(self):
        event = self.tc_deleted_event
        self.assertEqual(
            (event.project_id, event.target_type),
            (self.tc_project, "design"),
            msg=self.parameters.MSG_AUDITLOG_DELETED,
            abort_on_fail=False,
        )

    def bud_new_token_is_recorded_as_a_changed_field(self):
        event = self.tc_rotation_event
        self.print_variables({"details": event.details})
        self.assertEqual(
            (self.tc_rotation.status, "token" in event.details["fields"]),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_AUDITLOG_ROTATED,
            abort_on_fail=False,
        )

    def bud_record_does_not_contain_the_new_token(self):
        self.assertNotIn(
            self.parameters.AUDITLOG_SECRET,
            repr(self.tc_rotation_event.details),
            msg=self.parameters.MSG_AUDITLOG_NO_SECRET,
            abort_on_fail=False,
        )

    def bud_members_read_of_the_audit_log_is_refused_403(self):
        self.print_variables(
            {"status": self.tc_member_read.status, "body": self.tc_member_read.body}
        )
        self.assertEqual(
            self.tc_member_read.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_AUDITLOG_MEMBER_REFUSED,
            abort_on_fail=False,
        )

    def bud_administrator_reads_every_sign_in_record(self):
        body = self.tc_page.body
        self.print_variables({"total": body["total"]})
        self.assertEqual(
            (self.tc_page.status, body["total"], {item["action"] for item in body["items"]}),
            (self.parameters.STATUS_OK, self.tc_sign_ins, {self.parameters.AUDITLOG_LOGIN}),
            msg=self.parameters.MSG_AUDITLOG_FILTERED,
            abort_on_fail=False,
        )

    def bud_newest_record_names_the_administrator(self):
        self.assertEqual(
            self.tc_page.body["items"][0]["actor_name"],
            self.parameters.AUDITLOG_ADMIN_NAME,
            msg=self.parameters.MSG_AUDITLOG_NEWEST,
            abort_on_fail=False,
        )

    def bud_sorting_precedes_pagination(self):
        for (field, direction), hours in self.tc_sorted.items():
            index = self.parameters.AUDITLOG_DIRECTIONS.index(direction)
            self.assertEqual(
                hours,
                self.parameters.AUDITLOG_SORTED[field][index],
                msg=self.parameters.MSG_AUDITLOG_SORT.format(field=field, direction=direction),
                abort_on_fail=False,
            )

    def bud_unknown_sort_field_or_direction_is_refused_422(self):
        for query, status in zip(self.parameters.AUDITLOG_INVALID, self.tc_invalid):
            self.assertEqual(
                status,
                self.parameters.STATUS_UNPROCESSABLE,
                msg=self.parameters.MSG_AUDITLOG_INVALID.format(query=query),
                abort_on_fail=False,
            )

    def bud_every_audit_endpoint_is_a_get(self):
        self.assertEqual(
            self.tc_methods,
            ["GET"],
            msg=self.parameters.MSG_AUDITLOG_READ_ONLY,
            abort_on_fail=False,
        )
