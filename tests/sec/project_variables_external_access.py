"""
* @file     ${tests/sec/project_variables_external_access.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests who lists the parameters of a project.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project parameters an external reader asks for.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectVariablesExternalAccessBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_is_refused_the_parameters_403(self):
        self.print_variables({"status": self.tc_refused.status, "body": self.tc_refused.body})
        self.assertEqual(
            self.tc_refused.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_READER_VARIABLES_REFUSED,
            abort_on_fail=False,
        )

    def bud_member_with_every_permission_lists_the_parameter(self):
        self.print_variables({"status": self.tc_listed.status, "body": self.tc_listed.body})
        self.assertEqual(
            (self.tc_listed.status, [item["key"] for item in self.tc_listed.body]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VARIABLE_KEY]),
            msg=self.parameters.MSG_READER_VARIABLES_SHOWN,
            abort_on_fail=False,
        )
