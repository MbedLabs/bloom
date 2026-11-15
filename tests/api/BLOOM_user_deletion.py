"""
* @file     ${tests/api/BLOOM_user_deletion.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Deleting a user removes the user, also when the user is a project member.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the user delete route of the full app in-process.
"""

from types import SimpleNamespace

from tests.api.user_deletion import UserDeletionBase


class UserDeletionTest(UserDeletionBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_enforce_foreign_keys()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        plain_email, member_email = self.parameters.DELETION_EMAILS
        plain = self._create(plain_email)
        self.tc_plain = self._delete(plain)
        member = self._create(member_email)
        project = self.bloom.bloom_api_create_project(
            self.admin, self.parameters.DELETION_PREFIX
        ).json()
        policy = self.bloom.bloom_api_create_policy(
            self.admin,
            self.parameters.DELETION_POLICY,
            self.parameters.DELETION_PERMISSIONS,
            self.parameters.DELETION_DOC_TYPES,
            visibility=self.parameters.DELETION_VISIBILITY,
        ).json()
        added = self.bloom.bloom_api_add_project_member(
            self.admin, project.get("id"), member.json().get("id"), [policy.get("id")]
        )
        self.tc_member = self._delete(member)
        self.tc_member.member = added.status_code

    def tearDownClass(self):
        super().tearDownClass()

    def _create(self, email):
        """Create a user with the deletion role."""
        return self.bloom.bloom_api_create_user(
            self.admin, email, self.parameters.API_PASSWORD, self.parameters.DELETION_ROLE
        )

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


if __name__ == "__main__":
    UserDeletionTest().run()
