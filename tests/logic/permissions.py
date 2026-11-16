"""
* @file     ${tests/logic/permissions.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the permission vocabulary: baselines, policies and transitions.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the permission vocabulary.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class PermissionsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_role_baselines_match_the_role_gates(self):
        self.print_variables({"admin": self.admin, "maintainer alone": self.unassigned})
        self._equal(self.admin, self.parameters.PERM_ADMIN_BASELINE, self.parameters.MSG_PERM_ADMIN)
        self._equal(
            self.unassigned,
            self.parameters.PERM_NO_BASELINE,
            self.parameters.MSG_PERM_NO_MEMBERSHIP,
        )
        self._equal(
            sorted(self.maintainer),
            sorted(self.resources),
            self.parameters.MSG_PERM_MAINTAINER_RESOURCES,
        )
        self._equal(self.maintainer_delete, True, self.parameters.MSG_PERM_MAINTAINER_DELETE)
        self.assertNotIn(
            self.parameters.PERM_MEMBER_RESOURCE,
            self.resources,
            msg=self.parameters.MSG_PERM_NO_MEMBER_RESOURCE,
            abort_on_fail=False,
        )
        for (roles, action, resource), held in self.readers.items():
            expected = dict(((a, r), h) for a, r, h in self.parameters.PERM_READER_CHECKS)[
                (action, resource)
            ]
            self.print_variables(
                {"roles": roles, "action": action, "resource": resource, "held": held}
            )
            self._equal(held, expected, self.parameters.MSG_PERM_READER)

    def bud_merge_only_adds(self):
        for action, resource, expected in self.parameters.PERM_MERGE_CHECKS:
            held = self.merged[(action, resource)]
            self.print_variables({"action": action, "resource": resource, "held": held})
            self._equal(held, expected, self.parameters.MSG_PERM_MERGE)

    def bud_wildcards_cover_resources_and_actions(self):
        for (granted, action, resource, expected), held in zip(
            self.parameters.PERM_WILDCARDS, self.wildcards
        ):
            self.print_variables(
                {"granted": granted, "action": action, "resource": resource, "held": held}
            )
            self._equal(held, expected, self.parameters.MSG_PERM_WILDCARD)

    def bud_transitions_need_their_action(self):
        for (current, following, expected), action in zip(
            self.parameters.PERM_TRANSITIONS, self.transitions
        ):
            self.print_variables({"from": current, "to": following, "action": action})
            self._equal(action, expected, self.parameters.MSG_PERM_TRANSITION)

    def bud_invalid_entries_are_named_and_lists_sorted(self):
        self.print_variables({"valid": self.valid, "invalid": self.invalid, "lists": self.lists})
        self._equal(self.valid, [], self.parameters.MSG_PERM_VALID)
        self._equal(
            self.invalid, self.parameters.PERM_INVALID_MESSAGES, self.parameters.MSG_PERM_INVALID
        )
        self._equal(self.lists, self.parameters.PERM_LISTS, self.parameters.MSG_PERM_LISTS)

    def bud_project_members_are_not_in_the_vocabulary(self):
        self.print_variables({"entries": self.members})
        self._equal(
            self.members, self.parameters.PERM_MEMBER_MESSAGES, self.parameters.MSG_PERM_MEMBERS
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
