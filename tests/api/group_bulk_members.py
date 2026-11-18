"""
* @file     ${tests/api/group_bulk_members.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests adding several users to a group in one request.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the bulk group membership.
"""

from types import SimpleNamespace

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class GroupBulkMembersBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_bulk_members_persist_without_changing_the_group(self):
        added = self._bulk(self.persist_group, {"user_ids": self.persist_ids}).status
        group = self._read(self.persist_group) or {}
        members = sorted(member["user_id"] for member in group.get("members", []))
        self.print_variables({"added": added, "members": members, "group": group})
        self._equal(added, self.parameters.STATUS_CREATED, self.parameters.MSG_BULK_ADDED)
        self._equal(members, sorted(self.persist_ids), self.parameters.MSG_BULK_MEMBERS)
        self._equal(group.get("policy_ids"), [self.policy_id], self.parameters.MSG_BULK_POLICIES)
        self._equal(
            group.get("grants"), self.parameters.BULK_NO_GRANTS, self.parameters.MSG_BULK_GRANTS
        )

    def bud_unknown_user_adds_nobody(self):
        unknown = self._refused(self.unknown_group, [self.known, self.parameters.BULK_UNKNOWN_USER])
        self.print_variables({"answer": unknown.status, "members": unknown.members})
        self._equal(
            unknown.status,
            self.parameters.STATUS_NOT_FOUND,
            self.parameters.MSG_BULK_UNKNOWN,
        )
        self._equal(
            unknown.members,
            self.parameters.BULK_NO_MEMBERS,
            self.parameters.MSG_BULK_NONE_ADDED,
        )

    def bud_invalid_selections_are_refused(self):
        for selection, group in self.invalid_groups:
            outcome = self._refused(group, selection)
            self.print_variables(
                {"selection": selection, "answer": outcome.status, "members": outcome.members}
            )
            self._equal(
                outcome.status,
                self.parameters.STATUS_UNPROCESSABLE,
                self.parameters.MSG_BULK_INVALID,
            )
            self._equal(
                outcome.members,
                self.parameters.BULK_NO_MEMBERS,
                self.parameters.MSG_BULK_NONE_ADDED,
            )

    def bud_existing_member_is_kept_and_single_duplicate_conflicts(self):
        group = self.existing_group
        first, second = self.existing_ids
        single = self._bulk(group, {"user_id": first}).status
        bulk = self._bulk(group, {"user_ids": [first, second]}).status
        repeated = self._bulk(group, {"user_ids": [first, second]})
        members = sorted(member["user_id"] for member in (repeated.body or {}).get("members", []))
        duplicate = self._bulk(group, {"user_id": first}).status
        outcome = SimpleNamespace(
            single=single,
            bulk=bulk,
            repeated=repeated.status,
            members=members,
            ids=[first, second],
            duplicate=duplicate,
        )
        self.print_variables(vars(outcome))
        self._equal(outcome.single, self.parameters.STATUS_CREATED, self.parameters.MSG_BULK_SINGLE)
        self._equal(outcome.bulk, self.parameters.STATUS_CREATED, self.parameters.MSG_BULK_RETAINED)
        self._equal(
            outcome.repeated, self.parameters.STATUS_CREATED, self.parameters.MSG_BULK_REPEATED
        )
        self._equal(outcome.members, sorted(outcome.ids), self.parameters.MSG_BULK_MEMBERS)
        self._equal(
            outcome.duplicate, self.parameters.STATUS_CONFLICT, self.parameters.MSG_BULK_DUPLICATE
        )

    def bud_bulk_membership_needs_an_administrator(self):
        maintainer = self._refused(self.maintainer_group, [self.other], headers=self.actor)
        self.print_variables({"answer": maintainer.status, "members": maintainer.members})
        self._equal(
            maintainer.status,
            self.parameters.STATUS_FORBIDDEN,
            self.parameters.MSG_BULK_ADMIN_ONLY,
        )
        self._equal(
            maintainer.members,
            self.parameters.BULK_NO_MEMBERS,
            self.parameters.MSG_BULK_NONE_ADDED,
        )

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

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
