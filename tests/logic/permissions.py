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
        has = self.bloom.bloom_has_permission
        baseline = self.bloom.bloom_role_baseline
        admin = baseline(*self.parameters.PERM_ADMIN_ROLES)
        unassigned = baseline(*self.parameters.PERM_UNASSIGNED_ROLES)
        maintainer = baseline(*self.parameters.PERM_MAINTAINER_ROLES)
        maintainer_delete = has(maintainer, *self.parameters.PERM_MAINTAINER_CHECK)
        resources = self.bloom.bloom_permission_resources()
        readers = {
            (roles, action, resource): has(baseline(*roles), action, resource)
            for roles in self.parameters.PERM_READER_ROLES
            for action, resource, _ in self.parameters.PERM_READER_CHECKS
        }
        self.print_variables({"admin": admin, "maintainer alone": unassigned})
        self._equal(admin, self.parameters.PERM_ADMIN_BASELINE, self.parameters.MSG_PERM_ADMIN)
        self._equal(
            unassigned,
            self.parameters.PERM_NO_BASELINE,
            self.parameters.MSG_PERM_NO_MEMBERSHIP,
        )
        self._equal(
            sorted(maintainer),
            sorted(resources),
            self.parameters.MSG_PERM_MAINTAINER_RESOURCES,
        )
        self._equal(maintainer_delete, True, self.parameters.MSG_PERM_MAINTAINER_DELETE)
        self.assertNotIn(
            self.parameters.PERM_MEMBER_RESOURCE,
            resources,
            msg=self.parameters.MSG_PERM_NO_MEMBER_RESOURCE,
            abort_on_fail=False,
        )
        for (roles, action, resource), held in readers.items():
            expected = dict(((a, r), h) for a, r, h in self.parameters.PERM_READER_CHECKS)[
                (action, resource)
            ]
            self.print_variables(
                {"roles": roles, "action": action, "resource": resource, "held": held}
            )
            self._equal(held, expected, self.parameters.MSG_PERM_READER)

    def bud_merge_only_adds(self):
        merged = self.bloom.bloom_merge_permissions(
            self.bloom.bloom_role_baseline(*self.parameters.PERM_MERGE_ROLES),
            *self.parameters.PERM_MERGES,
        )
        for action, resource, expected in self.parameters.PERM_MERGE_CHECKS:
            held = self.bloom.bloom_has_permission(merged, action, resource)
            self.print_variables({"action": action, "resource": resource, "held": held})
            self._equal(held, expected, self.parameters.MSG_PERM_MERGE)

    def bud_wildcards_cover_resources_and_actions(self):
        for granted, action, resource, expected in self.parameters.PERM_WILDCARDS:
            held = self.bloom.bloom_has_permission(granted, action, resource)
            self.print_variables(
                {"granted": granted, "action": action, "resource": resource, "held": held}
            )
            self._equal(held, expected, self.parameters.MSG_PERM_WILDCARD)

    def bud_transitions_need_their_action(self):
        for current, following, expected in self.parameters.PERM_TRANSITIONS:
            action = self.bloom.bloom_transition_action(current, following)
            self.print_variables({"from": current, "to": following, "action": action})
            self._equal(action, expected, self.parameters.MSG_PERM_TRANSITION)

    def bud_invalid_entries_are_named_and_lists_sorted(self):
        valid = self.bloom.bloom_invalid_permission_entries(self.parameters.PERM_VALID_MATRIX)
        invalid = self.bloom.bloom_invalid_permission_entries(self.parameters.PERM_INVALID_MATRIX)
        lists = self.bloom.bloom_permissions_as_lists(self.parameters.PERM_LISTS_INPUT)
        self.print_variables({"valid": valid, "invalid": invalid, "lists": lists})
        self._equal(valid, [], self.parameters.MSG_PERM_VALID)
        self._equal(
            invalid, self.parameters.PERM_INVALID_MESSAGES, self.parameters.MSG_PERM_INVALID
        )
        self._equal(lists, self.parameters.PERM_LISTS, self.parameters.MSG_PERM_LISTS)

    def bud_project_members_are_not_in_the_vocabulary(self):
        members = self.bloom.bloom_invalid_permission_entries(self.parameters.PERM_MEMBER_MATRIX)
        self.print_variables({"entries": members})
        self._equal(members, self.parameters.PERM_MEMBER_MESSAGES, self.parameters.MSG_PERM_MEMBERS)

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
