"""
* @file     ${tests/logic/link_rules.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the link matrix and the tag rules between artefact kinds.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the link rules.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class LinkRulesBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_linkable_kinds_are_normalized(self):
        self._check(
            self.parameters.LINK_NORMALIZED, self.tc_normalized, self.parameters.MSG_LINK_NORMALIZED
        )

    def bud_pairs_allow_exactly_their_matrix_roles(self):
        rows = [((source, target), roles) for source, target, roles in self.parameters.LINK_ROLES]
        self._check(rows, self.tc_roles, self.parameters.MSG_LINK_ROLES)

    def bud_only_supported_kinds_are_linkable(self):
        self._check(self.parameters.LINK_KNOWN, self.tc_known, self.parameters.MSG_LINK_KNOWN)

    def bud_roles_follow_the_matrix(self):
        rows = [((s, t, role), allowed) for s, t, role, allowed in self.parameters.LINK_ROLE_CHECKS]
        self._check(rows, self.tc_role_checks, self.parameters.MSG_LINK_ROLE)

    def bud_only_prose_bodies_host_tags(self):
        self._check(
            self.parameters.LINK_TAG_HOSTS, self.tc_tag_hosts, self.parameters.MSG_LINK_TAG_HOST
        )

    def bud_tags_reach_known_kinds_from_tag_hosts(self):
        rows = [((s, t), allowed) for s, t, allowed in self.parameters.LINK_TAG_PAIRS]
        self._check(rows, self.tc_tag_pairs, self.parameters.MSG_LINK_TAG_PAIR)

    def _check(self, rows, answers, message):
        """Assert each row's answer equals its expected value."""
        for key, expected in rows:
            self.print_variables({"input": key, "answer": answers[key]})
            self.assertEqual(answers[key], expected, msg=message, abort_on_fail=False)
