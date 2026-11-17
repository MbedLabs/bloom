"""
* @file     ${tests/sec/project_iam_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what a member of one project gets of another project.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project boundaries over HTTP.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectIamHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_member_lists_only_their_project(self):
        projects = self.bloom.bloom_api_list_projects(self.member)
        self.print_variables({"status": projects.status, "body": projects.body})
        self.assertEqual(
            (projects.status, [item["id"] for item in projects.body]),
            (self.parameters.STATUS_OK, [self.allowed]),
            msg=self.parameters.MSG_IAMHTTP_PROJECTS,
            abort_on_fail=False,
        )

    def bud_requirements_of_another_project_are_refused_403(self):
        blocked_list = self.bloom.bloom_api_list_requirements(self.member, self.blocked)
        self.print_variables({"status": blocked_list.status, "body": blocked_list.body})
        self.assertEqual(
            blocked_list.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_LIST,
            abort_on_fail=False,
        )

    def bud_requirement_of_another_project_is_answered_404(self):
        blocked_read = self.bloom.bloom_api_read_requirement(self.member, self.requirement)
        self.print_variables({"status": blocked_read.status, "body": blocked_read.body})
        self.assertEqual(
            blocked_read.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_IAMHTTP_READ,
            abort_on_fail=False,
        )

    def bud_traceability_of_another_project_is_refused_403(self):
        blocked_traceability = self.bloom.bloom_api_traceability(self.member, self.blocked)
        self.print_variables(
            {
                "status": blocked_traceability.status,
                "body": blocked_traceability.body,
            }
        )
        self.assertEqual(
            blocked_traceability.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_TRACEABILITY,
            abort_on_fail=False,
        )

    def bud_dashboard_shows_only_the_members_project(self):
        dashboard = self.bloom.bloom_api_dashboard_stats(self.member)
        self.print_variables({"status": dashboard.status, "body": dashboard.body})
        self.assertEqual(
            (dashboard.status, [item["id"] for item in dashboard.body["projects"]]),
            (self.parameters.STATUS_OK, [self.allowed]),
            msg=self.parameters.MSG_IAMHTTP_DASHBOARD,
            abort_on_fail=False,
        )

    def bud_import_from_another_project_is_refused_403(self):
        blocked_import = self.bloom.bloom_api_import_from(
            self.member,
            self.allowed,
            self.blocked,
            self.parameters.IAMHTTP_DOC_TYPE,
            [self.requirement],
        )
        self.print_variables({"status": blocked_import.status, "body": blocked_import.body})
        self.assertEqual(
            blocked_import.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_IMPORT,
            abort_on_fail=False,
        )

    def bud_external_readers_reqif_upload_is_refused_403(self):
        reqif = self.bloom.bloom_api_upload_reqif(
            self.reader, self.allowed, self.parameters.IAMHTTP_REQIF
        )
        self.print_variables({"status": reqif.status, "body": reqif.body})
        self.assertEqual(
            reqif.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_REQIF,
            abort_on_fail=False,
        )
