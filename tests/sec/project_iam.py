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
        admin = self.bloom.bloom_require_project_access(self.parameters.IAM_ADMIN)
        self.print_variables(
            {
                "refusal": admin.status,
                "membership": admin.membership,
                "lookups": admin.lookups,
            }
        )
        self.assertEqual(
            admin.status,
            None,
            msg=self.parameters.MSG_IAM_ADMIN_ADMITTED,
            abort_on_fail=False,
        )
        self.assertEqual(
            admin.membership,
            None,
            msg=self.parameters.MSG_IAM_ADMIN_NO_MEMBERSHIP,
            abort_on_fail=False,
        )
        self.assertEqual(
            admin.lookups,
            self.parameters.IAM_PROJECT_LOOKUPS,
            msg=self.parameters.MSG_IAM_ADMIN_LOOKUP,
            abort_on_fail=False,
        )

    def bud_unassigned_user_is_refused(self):
        unassigned = self.bloom.bloom_require_project_access(self.parameters.IAM_MAINTAINER)
        self.print_variables({"refusal": unassigned.status})
        self.assertRegex(
            unassigned.detail,
            self.parameters.IAM_NOT_ASSIGNED,
            msg=self.parameters.MSG_IAM_UNASSIGNED,
            abort_on_fail=False,
        )

    def bud_missing_action_is_refused(self):
        missing = self.bloom.bloom_require_project_access(
            self.parameters.IAM_MAINTAINER,
            self.parameters.IAM_VIEW_ONLY,
            self.parameters.IAM_EDIT_REQUIREMENT,
        )
        self.print_variables({"refusal": missing.status})
        self.assertRegex(
            missing.detail,
            self.parameters.IAM_MISSING_PERMISSION,
            msg=self.parameters.MSG_IAM_MISSING_ACTION,
            abort_on_fail=False,
        )

    def bud_explicit_action_is_admitted(self):
        granted = self.bloom.bloom_require_project_access(
            self.parameters.IAM_MAINTAINER,
            self.parameters.IAM_VIEW_AND_EDIT,
            self.parameters.IAM_EDIT_REQUIREMENT,
        )
        self.print_variables({"refusal": granted.status, "detail": granted.detail})
        self.assertEqual(
            granted.status,
            None,
            msg=self.parameters.MSG_IAM_EXPLICIT_ACTION,
            abort_on_fail=False,
        )
