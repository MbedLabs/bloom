"""
* @file     ${tests/api/group_bulk_members.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests adding several users to a group in one request.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the bulk group membership.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class GroupBulkMembersBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_bulk_members_persist_without_changing_the_group(self):
        group = self.tc_persist.group or {}
        members = sorted(member["user_id"] for member in group.get("members", []))
        self.print_variables({"added": self.tc_persist.added, "members": members, "group": group})
        self._equal(
            self.tc_persist.added, self.parameters.STATUS_CREATED, self.parameters.MSG_BULK_ADDED
        )
        self._equal(members, sorted(self.tc_persist.ids), self.parameters.MSG_BULK_MEMBERS)
        self._equal(
            group.get("policy_ids"), [self.tc_persist.policy_id], self.parameters.MSG_BULK_POLICIES
        )
        self._equal(
            group.get("grants"), self.parameters.BULK_NO_GRANTS, self.parameters.MSG_BULK_GRANTS
        )

    def bud_unknown_user_adds_nobody(self):
        self.print_variables({"answer": self.tc_unknown.status, "members": self.tc_unknown.members})
        self._equal(
            self.tc_unknown.status,
            self.parameters.STATUS_NOT_FOUND,
            self.parameters.MSG_BULK_UNKNOWN,
        )
        self._equal(
            self.tc_unknown.members,
            self.parameters.BULK_NO_MEMBERS,
            self.parameters.MSG_BULK_NONE_ADDED,
        )

    def bud_invalid_selections_are_refused(self):
        for selection, outcome in self.tc_invalid:
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
        outcome = self.tc_existing
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
        self.print_variables(
            {"answer": self.tc_maintainer.status, "members": self.tc_maintainer.members}
        )
        self._equal(
            self.tc_maintainer.status,
            self.parameters.STATUS_FORBIDDEN,
            self.parameters.MSG_BULK_ADMIN_ONLY,
        )
        self._equal(
            self.tc_maintainer.members,
            self.parameters.BULK_NO_MEMBERS,
            self.parameters.MSG_BULK_NONE_ADDED,
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
