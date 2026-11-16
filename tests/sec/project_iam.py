"""
* @file     ${tests/sec/project_iam.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests who is admitted to a project and with which actions.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the project admission check.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ProjectIamBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_admin_is_admitted_without_membership(self):
        self.print_variables(
            {
                "refusal": self.admin.status,
                "membership": self.admin.membership,
                "lookups": self.admin.lookups,
            }
        )
        self.assertEqual(
            self.admin.status,
            None,
            msg=self.parameters.MSG_IAM_ADMIN_ADMITTED,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.admin.membership,
            None,
            msg=self.parameters.MSG_IAM_ADMIN_NO_MEMBERSHIP,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.admin.lookups,
            self.parameters.IAM_PROJECT_LOOKUPS,
            msg=self.parameters.MSG_IAM_ADMIN_LOOKUP,
            abort_on_fail=False,
        )

    def bud_unassigned_user_is_refused(self):
        self.print_variables({"refusal": self.unassigned.status})
        self.assertRegex(
            self.unassigned.detail,
            self.parameters.IAM_NOT_ASSIGNED,
            msg=self.parameters.MSG_IAM_UNASSIGNED,
            abort_on_fail=False,
        )

    def bud_missing_action_is_refused(self):
        self.print_variables({"refusal": self.missing.status})
        self.assertRegex(
            self.missing.detail,
            self.parameters.IAM_MISSING_PERMISSION,
            msg=self.parameters.MSG_IAM_MISSING_ACTION,
            abort_on_fail=False,
        )

    def bud_explicit_action_is_admitted(self):
        self.print_variables({"refusal": self.granted.status, "detail": self.granted.detail})
        self.assertEqual(
            self.granted.status,
            None,
            msg=self.parameters.MSG_IAM_EXPLICIT_ACTION,
            abort_on_fail=False,
        )
