"""
* @file     ${tests/api/BLOOM_group_bulk_members.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A bulk membership request adds all users or none, and only an admin may send it.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the group member route of the full app in-process.
"""

from tests.api.group_bulk_members import GroupBulkMembersBase


class GroupBulkMembersTest(GroupBulkMembersBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        self.admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        emails = iter(self.parameters.BULK_EMAILS)
        groups = iter(self.parameters.BULK_GROUP_NAMES)
        policy = self.bloom.bloom_api_create_policy_rules(
            self.admin, self.parameters.BULK_POLICY_NAME, self.parameters.BULK_POLICY_RULES
        ).json()
        self.policy_id = policy["id"]
        self.persist_group = self._group(next(groups), [self.policy_id])
        self.persist_ids = [
            self._user(next(emails), self.parameters.BULK_EXTERNAL) for _ in range(2)
        ]
        self.unknown_group = self._group(next(groups))
        self.known = self._user(next(emails), self.parameters.BULK_EXTERNAL)
        self.invalid_groups = [
            (selection, self._group(next(groups)))
            for selection in self.parameters.BULK_INVALID_SELECTIONS
        ]
        self.existing_group = self._group(next(groups))
        self.existing_ids = [
            self._user(next(emails), self.parameters.BULK_EXTERNAL) for _ in range(2)
        ]
        self.maintainer_group = self._group(next(groups))
        actor_email = next(emails)
        self._user(actor_email, self.parameters.BULK_MAINTAINER)
        self.other = self._user(next(emails), self.parameters.BULK_MAINTAINER)
        self.actor, _ = self.bloom.bloom_log_in(actor_email, self.parameters.API_PASSWORD)

    def tearDownClass(self):
        super().tearDownClass()

    def _group(self, name, policy_ids=()):
        """Create a group and return its id."""
        return (
            self.bloom.bloom_api_create_group(self.admin, name, list(policy_ids)).json().get("id")
        )

    def _user(self, email, role):
        """Create a user and return their id."""
        created = self.bloom.bloom_api_create_user(
            self.admin, email, self.parameters.API_PASSWORD, role
        )
        return created.json().get("id")


if __name__ == "__main__":
    GroupBulkMembersTest().run()
