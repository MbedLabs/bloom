"""
* @file     ${tests/api/user_deletion.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests deleting users, project members included.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the user deletion.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class UserDeletionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_plain_user_is_deleted(self):
        self._assert_deleted(self.tc_plain)

    def bud_project_member_is_deleted(self):
        self.print_variables({"member": self.tc_member.member})
        self.assertIn(
            self.tc_member.member,
            self.parameters.DELETION_ACCEPTED,
            msg=self.parameters.MSG_DELETION_MEMBER,
            abort_on_fail=False,
        )
        self._assert_deleted(self.tc_member)

    def _assert_deleted(self, outcome):
        """Assert the user was created, deleted with 204 and is absent from the user list."""
        self.print_variables(vars(outcome))
        self.assertIn(
            outcome.created,
            self.parameters.DELETION_ACCEPTED,
            msg=self.parameters.MSG_DELETION_CREATED,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.deleted,
            self.parameters.STATUS_NO_CONTENT,
            msg=self.parameters.MSG_DELETION_ANSWER,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.listed,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_DELETION_LISTED,
            abort_on_fail=False,
        )
        self.assertNotIn(
            outcome.user_id,
            outcome.remaining,
            msg=self.parameters.MSG_DELETION_GONE,
            abort_on_fail=False,
        )
