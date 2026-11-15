"""
* @file     ${tests/logic/tag_links.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests turning tags in a document body into reference links.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     Base class containing the bud methods of the tag link sync.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class TagLinksBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_invalid_tag_pairs_are_refused(self):
        for (source, target), (outcome, links) in self.tc_invalid.items():
            self.print_variables(
                {"pair": (source, target), "outcome": vars(outcome), "links": links}
            )
            self._equal(
                outcome.status,
                self.parameters.STATUS_UNPROCESSABLE,
                self.parameters.MSG_TAG_REFUSED,
            )
            for kind in (source, target):
                self.assertIn(
                    kind,
                    outcome.detail,
                    msg=self.parameters.MSG_TAG_REFUSAL_NAMES,
                    abort_on_fail=False,
                )
            self._equal(links, self.parameters.TAG_NO_LINKS, self.parameters.MSG_TAG_NO_LINK)

    def bud_hidden_tag_is_skipped(self):
        outcome, links = self.tc_hidden
        self.print_variables({"outcome": vars(outcome), "links": links})
        self._equal(
            outcome.created, self.parameters.TAG_NONE_CREATED, self.parameters.MSG_TAG_HIDDEN
        )
        self._equal(links, self.parameters.TAG_NO_LINKS, self.parameters.MSG_TAG_NO_LINK)

    def bud_self_tag_is_skipped(self):
        self.print_variables(vars(self.tc_self))
        self._equal(
            self.tc_self.created, self.parameters.TAG_NONE_CREATED, self.parameters.MSG_TAG_SELF
        )

    def bud_tag_creates_one_reference_link(self):
        self.print_variables(
            {"first": vars(self.tc_first), "links": self.tc_links, "again": vars(self.tc_again)}
        )
        self._equal(
            self.tc_first.created, self.parameters.TAG_CREATED, self.parameters.MSG_TAG_CREATED
        )
        self._equal(self.tc_links, [self.parameters.TAG_LINK], self.parameters.MSG_TAG_LINK)
        self._equal(
            self.tc_again.created,
            self.parameters.TAG_NONE_CREATED,
            self.parameters.MSG_TAG_REPEATED,
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
