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
        self.assertEqual(
            (self.projects.status, [item["id"] for item in self.projects.body]),
            (self.parameters.STATUS_OK, [self.allowed]),
            msg=self.parameters.MSG_IAMHTTP_PROJECTS,
            abort_on_fail=False,
        )

    def bud_requirements_of_another_project_are_refused_403(self):
        self.print_variables({"status": self.blocked_list.status, "body": self.blocked_list.body})
        self.assertEqual(
            self.blocked_list.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_LIST,
            abort_on_fail=False,
        )

    def bud_requirement_of_another_project_is_answered_404(self):
        self.print_variables({"status": self.blocked_read.status, "body": self.blocked_read.body})
        self.assertEqual(
            self.blocked_read.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_IAMHTTP_READ,
            abort_on_fail=False,
        )

    def bud_traceability_of_another_project_is_refused_403(self):
        self.print_variables(
            {
                "status": self.blocked_traceability.status,
                "body": self.blocked_traceability.body,
            }
        )
        self.assertEqual(
            self.blocked_traceability.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_TRACEABILITY,
            abort_on_fail=False,
        )

    def bud_dashboard_shows_only_the_members_project(self):
        self.assertEqual(
            (self.dashboard.status, [item["id"] for item in self.dashboard.body["projects"]]),
            (self.parameters.STATUS_OK, [self.allowed]),
            msg=self.parameters.MSG_IAMHTTP_DASHBOARD,
            abort_on_fail=False,
        )

    def bud_import_from_another_project_is_refused_403(self):
        self.print_variables(
            {"status": self.blocked_import.status, "body": self.blocked_import.body}
        )
        self.assertEqual(
            self.blocked_import.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_IMPORT,
            abort_on_fail=False,
        )

    def bud_external_readers_reqif_upload_is_refused_403(self):
        self.print_variables({"status": self.reqif.status, "body": self.reqif.body})
        self.assertEqual(
            self.reqif.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_IAMHTTP_REQIF,
            abort_on_fail=False,
        )
