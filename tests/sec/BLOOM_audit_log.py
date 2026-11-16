"""
* @file     ${tests/sec/BLOOM_audit_log.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The audit log records sign-ins and changes without secrets, and only administrators read it, sorted before paged.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the API and the audit records with one administrator and four accounts.
"""

from tests.sec.audit_log import AuditLogBase


class AuditLogTest(AuditLogBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        password, role = values.API_PASSWORD, values.API_MEMBER_ROLE
        last = lambda action: bloom.bloom_list_audit_events(action)[-1]
        bloom.bloom_start_full_api()
        self.tc_someone = bloom.bloom_add_account(values.AUDITLOG_SOMEONE, password, role)
        self.tc_refused_login = bloom.bloom_api_try_log_in(
            values.AUDITLOG_SOMEONE, values.HTTP_WRONG_PASSWORD
        )
        self.tc_failed_event = last(values.AUDITLOG_LOGIN)

        self.tc_member = bloom.bloom_add_account(values.AUDITLOG_MEMBER, password, role)
        member, _ = bloom.bloom_log_in(values.AUDITLOG_MEMBER, password)
        self.tc_login_event = last(values.AUDITLOG_LOGIN)

        self.tc_admin = bloom.bloom_add_account(
            values.AUDITLOG_ADMIN, password, values.EMAIL_ADMIN_ROLE, values.AUDITLOG_ADMIN_NAME
        )
        admin, _ = bloom.bloom_log_in(values.AUDITLOG_ADMIN, password)
        self.tc_demoted = bloom.bloom_add_account(values.AUDITLOG_DEMOTED, password, role)
        self.tc_role_change = bloom.bloom_api_set_role(admin, self.tc_demoted, values.EXTERNAL_ROLE)
        self.tc_role_event = last("user.role_changed")

        self.tc_project = bloom.bloom_create_project(values.AUDITLOG_PREFIX)
        design = bloom.bloom_add_design(self.tc_project, values.AUDITLOG_DESIGN)
        policy = bloom.bloom_api_create_policy_rules(
            admin, values.AUDITLOG_POLICY, bloom.bloom_rules_for(values.READER_ALL_PERMISSIONS)
        )
        added = bloom.bloom_api_add_project_member(
            admin, self.tc_project, self.tc_member, [policy.json()["id"]]
        )
        changed = bloom.bloom_api_set_design_visibility(admin, design, values.CUSTOMER_VISIBILITY)
        deleted = bloom.bloom_api_delete_design(admin, design)
        self.tc_statuses = (added.status_code, changed.status, deleted.status)
        self.tc_member_event = last("project_member.added")
        self.tc_visibility_event = last("artefact.visibility_changed")
        self.tc_deleted_event = last("artefact.deleted")

        setting = bloom.bloom_create_integration(self.tc_project)
        self.tc_rotation = bloom.bloom_api_rotate_setting_token(
            admin, setting, values.AUDITLOG_SECRET
        )
        self.tc_rotation_event = last("integration.updated")

        self.tc_member_read = bloom.bloom_api_audit(member, sort="actor", dir="asc")
        admin, _ = bloom.bloom_log_in(values.AUDITLOG_ADMIN, password)
        self.tc_sign_ins = len(bloom.bloom_list_audit_events(values.AUDITLOG_LOGIN))
        self.tc_page = bloom.bloom_api_audit(admin, action=values.AUDITLOG_AUTH_FILTER)

        actors = {
            "ada": bloom.bloom_add_account(
                values.AUDITLOG_ADA[0], password, role, values.AUDITLOG_ADA[1]
            ),
            "zoe": bloom.bloom_add_account(
                values.AUDITLOG_ZOE[0], password, role, values.AUDITLOG_ZOE[1]
            ),
        }
        hours = values.AUDITLOG_SORT_HOURS
        hour_of = dict(
            zip(bloom.bloom_add_audit_events(hours, values.AUDITLOG_SORT_ROWS, actors), hours)
        )
        self.tc_sorted = {}
        for field in values.AUDITLOG_SORTED:
            for direction in values.AUDITLOG_DIRECTIONS:
                pages = bloom.bloom_api_audit_pages(
                    admin, values.AUDITLOG_SORT_FILTER, field, direction
                )
                self.tc_sorted[(field, direction)] = (
                    [hour_of[event_id] for event_id in pages] if isinstance(pages, list) else pages
                )
        self.tc_invalid = [
            bloom.bloom_api_audit(admin, **query).status for query in values.AUDITLOG_INVALID
        ]
        self.tc_methods = bloom.bloom_route_methods_of(values.AUDITLOG_MODULE)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AuditLogTest().run()
