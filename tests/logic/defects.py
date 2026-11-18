"""
* @file     ${tests/logic/defects.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests defect links, issue links and webhook signatures.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the defect rules.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class DefectsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_defects_and_campaigns_are_linkable(self):
        self.assertEqual(
            (self.bloom.bloom_linkable("DEF"), self.bloom.bloom_linkable("CMP")),
            (True, True),
            msg=self.parameters.MSG_DFX_LINKABLE,
            abort_on_fail=False,
        )

    def bud_references_are_the_only_role_between_these_pairs(self):
        for source, target in self.parameters.DFX_EXACT_ROLES:
            self.assertEqual(
                self.bloom.bloom_link_roles(source, target),
                ("references",),
                msg=self.parameters.MSG_DFX_EXACT.format(source=source, target=target),
                abort_on_fail=False,
            )

    def bud_these_pairs_allow_their_named_roles(self):
        for source, target, roles in self.parameters.DFX_INCLUDED_ROLES:
            allowed = self.bloom.bloom_link_roles(source, target)
            self.print_variables({f"{source} to {target}": allowed})
            self.assertTrue(
                set(roles) <= set(allowed),
                msg=self.parameters.MSG_DFX_INCLUDED.format(
                    source=source, target=target, roles=roles
                ),
                abort_on_fail=False,
            )

    def bud_a_defect_cannot_be_linked_to_a_baseline(self):
        self.assertEqual(
            (
                self.bloom.bloom_link_roles("DEF", "BL"),
                self.bloom.bloom_link_role_allowed("DEF", "BL", "references"),
            ),
            ((), False),
            msg=self.parameters.MSG_DFX_FORBIDDEN,
            abort_on_fail=False,
        )

    def bud_a_github_issue_link_is_read(self):
        self.assertEqual(
            self.bloom.bloom_parse_issue_link(self.parameters.DFX_GITHUB, "github"),
            ("github", "octocat/Hello-World", 42),
            msg=self.parameters.MSG_DFX_GITHUB,
            abort_on_fail=False,
        )

    def bud_a_gitlab_issue_link_is_read(self):
        self.assertEqual(
            (
                self.bloom.bloom_parse_issue_link(self.parameters.DFX_GITLAB, "gitlab"),
                self.bloom.bloom_parse_issue_link(self.parameters.DFX_GITLAB_NESTED, "gitlab"),
            ),
            (("gitlab", "mygroup/myproject", 7), ("gitlab", "org/sub/project", 99)),
            msg=self.parameters.MSG_DFX_GITLAB,
            abort_on_fail=False,
        )

    def bud_links_that_are_not_issues_read_as_nothing(self):
        self.assertEqual(
            (
                self.bloom.bloom_parse_issue_link("https://github.com/octocat", "github"),
                self.bloom.bloom_parse_issue_link(
                    "https://gitlab.com/group/project/-/issues/1", "github"
                ),
                self.bloom.bloom_parse_issue_link(
                    "https://github.com/user/repo/issues/1", "gitlab"
                ),
            ),
            (None, None, None),
            msg=self.parameters.MSG_DFX_NOT_AN_ISSUE,
            abort_on_fail=False,
        )

    def bud_an_issue_link_is_read_by_its_tracker(self):
        self.assertEqual(
            (
                self.bloom.bloom_parse_issue_link("https://github.com/owner/repo/issues/10"),
                self.bloom.bloom_parse_issue_link("https://gitlab.com/ns/proj/-/issues/3"),
            ),
            (("github", "owner/repo", 10), ("gitlab", "ns/proj", 3)),
            msg=self.parameters.MSG_DFX_DETECT,
            abort_on_fail=False,
        )

    def bud_matching_external_fields_are_accepted(self):
        self.assertEqual(
            (
                self.bloom.bloom_check_external_fields(
                    "github", self.parameters.DFX_ISSUE, "owner/repo", 5
                ),
                self.bloom.bloom_check_external_fields(None, None, None, None),
            ),
            (None, None),
            msg=self.parameters.MSG_DFX_VALID,
            abort_on_fail=False,
        )

    def bud_mismatching_external_fields_are_refused(self):
        for what, fields, phrase in self.parameters.DFX_MISMATCHES:
            refusal = self.bloom.bloom_check_external_fields(*fields)
            self.print_variables({what: refusal})
            self.assertIn(
                phrase,
                (refusal or "").lower(),
                msg=self.parameters.MSG_DFX_MISMATCH.format(what=what),
                abort_on_fail=False,
            )

    def bud_a_github_signature_is_checked(self):
        values = self.parameters
        signature = self.bloom.bloom_github_signature(values.DFX_BODY, values.DFX_SECRET)
        self.assertEqual(
            (
                self.bloom.bloom_github_signature_accepted(
                    values.DFX_BODY, values.DFX_SECRET, signature
                ),
                self.bloom.bloom_github_signature_accepted(
                    values.DFX_BODY, values.DFX_SECRET, "sha256=wrong"
                ),
            ),
            (True, False),
            msg=values.MSG_DFX_SIGNATURE,
            abort_on_fail=False,
        )

    def bud_a_gitlab_token_is_checked(self):
        self.assertEqual(
            (
                self.bloom.bloom_gitlab_token_accepted("secret-token", "secret-token"),
                self.bloom.bloom_gitlab_token_accepted("secret-token", "wrong-token"),
            ),
            (True, False),
            msg=self.parameters.MSG_DFX_TOKEN,
            abort_on_fail=False,
        )
