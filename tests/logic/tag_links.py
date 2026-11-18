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
        for source, target in self.parameters.TAG_INVALID_PAIRS:
            outcome = self._sync(source, self.bloom.bloom_mention(target, self.target_id))
            links = self.bloom.bloom_list_links()
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
        outcome = self._sync(hidden=True)
        links = self.bloom.bloom_list_links()
        self.print_variables({"outcome": vars(outcome), "links": links})
        self._equal(
            outcome.created, self.parameters.TAG_NONE_CREATED, self.parameters.MSG_TAG_HIDDEN
        )
        self._equal(links, self.parameters.TAG_NO_LINKS, self.parameters.MSG_TAG_NO_LINK)

    def bud_self_tag_is_skipped(self):
        outcome = self._sync(
            content=self.bloom.bloom_mention(self.parameters.TAG_KIND, self.source_id)
        )
        self.print_variables(vars(outcome))
        self._equal(outcome.created, self.parameters.TAG_NONE_CREATED, self.parameters.MSG_TAG_SELF)

    def bud_tag_creates_one_reference_link(self):
        first = self._sync()
        links = self.bloom.bloom_list_links()
        again = self._sync()
        self.print_variables({"first": vars(first), "links": links, "again": vars(again)})
        self._equal(first.created, self.parameters.TAG_CREATED, self.parameters.MSG_TAG_CREATED)
        self._equal(links, [self.parameters.TAG_LINK], self.parameters.MSG_TAG_LINK)
        self._equal(
            again.created,
            self.parameters.TAG_NONE_CREATED,
            self.parameters.MSG_TAG_REPEATED,
        )

    def _sync(self, source=None, content=None, hidden=False):
        """Sync the source requirement's tag links; its content mentions the target by default."""
        kind = self.parameters.TAG_KIND
        if content is None:
            content = self.bloom.bloom_mention(kind, self.target_id)
        return self.bloom.bloom_sync_tag_links(
            self.project_id, source or kind, self.source_id, content, hidden
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
