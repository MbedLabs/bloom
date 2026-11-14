"""
* @file     ${tests/logic/BLOOM_permissions.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Role baselines, policy merges, wildcards and transitions grant the expected actions.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the permission functions against fixed tables.
"""

from tests.logic.permissions import PermissionsBase


class PermissionsTest(PermissionsBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        has = bloom.bloom_has_permission
        self.tc_admin = bloom.bloom_role_baseline(*self.parameters.PERM_ADMIN_ROLES)
        self.tc_unassigned = bloom.bloom_role_baseline(*self.parameters.PERM_UNASSIGNED_ROLES)
        self.tc_maintainer = bloom.bloom_role_baseline(*self.parameters.PERM_MAINTAINER_ROLES)
        self.tc_maintainer_delete = has(self.tc_maintainer, *self.parameters.PERM_MAINTAINER_CHECK)
        self.tc_resources = bloom.bloom_permission_resources()
        self.tc_readers = {
            (roles, action, resource): has(bloom.bloom_role_baseline(*roles), action, resource)
            for roles in self.parameters.PERM_READER_ROLES
            for action, resource, _ in self.parameters.PERM_READER_CHECKS
        }
        merged = bloom.bloom_merge_permissions(
            bloom.bloom_role_baseline(*self.parameters.PERM_MERGE_ROLES),
            *self.parameters.PERM_MERGES,
        )
        self.tc_merged = {
            (action, resource): has(merged, action, resource)
            for action, resource, _ in self.parameters.PERM_MERGE_CHECKS
        }
        self.tc_wildcards = [
            has(granted, action, resource)
            for granted, action, resource, _ in self.parameters.PERM_WILDCARDS
        ]
        self.tc_transitions = [
            bloom.bloom_transition_action(current, following)
            for current, following, _ in self.parameters.PERM_TRANSITIONS
        ]
        self.tc_valid = bloom.bloom_invalid_permission_entries(self.parameters.PERM_VALID_MATRIX)
        self.tc_invalid = bloom.bloom_invalid_permission_entries(
            self.parameters.PERM_INVALID_MATRIX
        )
        self.tc_lists = bloom.bloom_permissions_as_lists(self.parameters.PERM_LISTS_INPUT)
        self.tc_members = bloom.bloom_invalid_permission_entries(self.parameters.PERM_MEMBER_MATRIX)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    PermissionsTest().run()
