"""
* @file     ${tests/api/BLOOM_group_bulk_members.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A bulk membership request adds all users or none, and only an admin may send it.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the group member route of the full app in-process.
"""

from types import SimpleNamespace

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
        group = self._group(next(groups), [policy["id"]])
        ids = [self._user(next(emails), self.parameters.BULK_EXTERNAL) for _ in range(2)]
        added = self._bulk(group, {"user_ids": ids})
        self.tc_persist = SimpleNamespace(
            added=added.status, ids=ids, policy_id=policy["id"], group=self._read(group)
        )
        group = self._group(next(groups))
        known = self._user(next(emails), self.parameters.BULK_EXTERNAL)
        self.tc_unknown = self._refused(group, [known, self.parameters.BULK_UNKNOWN_USER])
        self.tc_invalid = []
        for selection in self.parameters.BULK_INVALID_SELECTIONS:
            self.tc_invalid.append(
                (
                    selection,
                    self._refused(self._group(next(groups)), selection),
                )
            )
        group = self._group(next(groups))
        first, second = (self._user(next(emails), self.parameters.BULK_EXTERNAL) for _ in range(2))
        single = self._bulk(group, {"user_id": first}).status
        bulk = self._bulk(group, {"user_ids": [first, second]}).status
        repeated = self._bulk(group, {"user_ids": [first, second]})
        members = sorted(member["user_id"] for member in (repeated.body or {}).get("members", []))
        duplicate = self._bulk(group, {"user_id": first}).status
        self.tc_existing = SimpleNamespace(
            single=single,
            bulk=bulk,
            repeated=repeated.status,
            members=members,
            ids=[first, second],
            duplicate=duplicate,
        )
        group = self._group(next(groups))
        actor_email = next(emails)
        self._user(actor_email, self.parameters.BULK_MAINTAINER)
        other = self._user(next(emails), self.parameters.BULK_MAINTAINER)
        actor, _ = self.bloom.bloom_log_in(actor_email, self.parameters.API_PASSWORD)
        self.tc_maintainer = self._refused(group, [other], headers=actor)

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

    def _bulk(self, group_id, body, headers=None):
        """Send a member request to the group."""
        return self.bloom.bloom_api_send_group_members(headers or self.admin, group_id, body)

    def _read(self, group_id):
        """Read the group as the admin."""
        return self.bloom.bloom_api_get_group(self.admin, group_id).json()

    def _refused(self, group_id, user_ids, headers=None):
        """Send a bulk request and return its status and the group's members afterwards."""
        answer = self._bulk(group_id, {"user_ids": user_ids}, headers)
        members = (self._read(group_id) or {}).get("members", [])
        return SimpleNamespace(status=answer.status, members=members)


if __name__ == "__main__":
    GroupBulkMembersTest().run()
