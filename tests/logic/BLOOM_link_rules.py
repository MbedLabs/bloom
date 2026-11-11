"""
* @file     ${tests/logic/BLOOM_link_rules.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Links follow the explicit matrix; tags reach any known kind from a prose body.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests normalization, matrix rows, roles, tag hosts and tag pairs.
"""

from tests.logic.link_rules import LinkRulesBase


class LinkRulesTest(LinkRulesBase):

    def setUpClass(self):
        super().setUpClass()
        rule = self.bloom.bloom_link_rule
        self.tc_normalized = {
            value: rule("normalize_linkable_type", value)
            for value, _ in self.parameters.LINK_NORMALIZED
        }
        self.tc_roles = {
            (source, target): rule("get_allowed_link_roles", source, target)
            for source, target, _ in self.parameters.LINK_ROLES
        }
        self.tc_known = {
            kind: rule("is_known_linkable_type", kind) for kind, _ in self.parameters.LINK_KNOWN
        }
        self.tc_role_checks = {
            (source, target, role): rule("is_allowed_link_role", source, target, role)
            for source, target, role, _ in self.parameters.LINK_ROLE_CHECKS
        }
        self.tc_tag_hosts = {
            kind: rule("is_tag_host_type", kind) for kind, _ in self.parameters.LINK_TAG_HOSTS
        }
        self.tc_tag_pairs = {
            (source, target): rule("is_allowed_tag_pair", source, target)
            for source, target, _ in self.parameters.LINK_TAG_PAIRS
        }

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    LinkRulesTest().run()
