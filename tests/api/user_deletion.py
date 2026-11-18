"""
* @file     ${tests/api/user_deletion.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests deleting users, project members included.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the user deletion.
"""

from types import SimpleNamespace

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class UserDeletionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_plain_user_is_deleted(self):
        self._assert_deleted(self._delete(self.plain))

    def bud_project_member_is_deleted(self):
        self.print_variables({"member": self.membership.status_code})
        self.assertIn(
            self.membership.status_code,
            self.parameters.DELETION_ACCEPTED,
            msg=self.parameters.MSG_DELETION_MEMBER,
            abort_on_fail=False,
        )
        self._assert_deleted(self._delete(self.member))

    def _delete(self, created):
        """Delete the created user and list the users afterwards."""
        user_id = created.json().get("id")
        deleted = self.bloom.bloom_api_delete_user(self.admin, user_id)
        listed, remaining = self.bloom.bloom_api_list_user_ids(self.admin)
        return SimpleNamespace(
            created=created.status_code,
            deleted=deleted.status,
            listed=listed,
            user_id=user_id,
            remaining=remaining,
        )

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
