"""
* @file     ${tests/logic/defect_managers.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Defect Managers group and who receives the email of a failed Jira send.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     Base class containing the bud methods of BLOOM-134, the defect manager policy group.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class DefectManagersBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_defect_managers_is_a_default_group_a_user_holds_on_a_project(self):
        policies = self.bloom.bloom_group_policy_names(self.parameters.DM_GROUP)
        self.print_variables({"policies": policies})
        self.assertEqual(
            policies, sorted(self.parameters.DM_POLICIES), msg=self.parameters.MSG_DM_GROUP
        )

    def bud_defect_managers_of_the_project_receive_the_failure_email(self):
        recipients = self.bloom.bloom_failure_recipient_emails(self.project_id)
        self.print_variables({"recipients": recipients})
        self.assertEqual(
            recipients,
            sorted(
                [self.parameters.DM_ADMIN, self.parameters.DM_OWNER, self.parameters.DM_MANAGER]
            ),
            msg=self.parameters.MSG_DM_RECIPIENTS,
            abort_on_fail=False,
        )
