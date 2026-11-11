"""
* @file     ${tests/logic/document_kinds.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests shared-document kinds: legacy values, the public API and slugs.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the document kinds.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class DocumentKindsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_legacy_kinds_map_to_canonical_codes(self):
        for value, expected in self.parameters.DOC_KIND_LEGACY:
            self.print_variables({"stored": value, "kind": self.tc_normalized[value]})
            self.assertEqual(
                self.tc_normalized[value],
                expected,
                msg=self.parameters.MSG_DOC_KIND_LEGACY,
                abort_on_fail=False,
            )

    def bud_public_api_accepts_only_canonical_kinds(self):
        for value in self.parameters.DOC_KIND_ACCEPTED:
            self.print_variables({"kind": value, "answer": vars(self.tc_required[value])})
            self.assertEqual(
                self.tc_required[value].kind,
                value,
                msg=self.parameters.MSG_DOC_KIND_ACCEPTED,
                abort_on_fail=False,
            )
        for value in self.parameters.DOC_KIND_REFUSED:
            answer = self.tc_required[value]
            self.print_variables({"kind": value, "status": answer.status})
            self.assertEqual(
                answer.status,
                self.parameters.STATUS_UNPROCESSABLE_ENTITY,
                msg=self.parameters.MSG_DOC_KIND_REFUSED,
                abort_on_fail=False,
            )
            for phrase in self.parameters.DOC_KIND_REFUSAL_PHRASES:
                self.assertIn(
                    phrase,
                    answer.detail,
                    msg=self.parameters.MSG_DOC_KIND_REFUSAL_TEXT,
                    abort_on_fail=False,
                )

    def bud_route_slugs_map_to_kinds(self):
        for slug, expected in self.parameters.DOC_KIND_SLUGS:
            self.print_variables({"slug": slug, "kind": self.tc_slugs[slug]})
            self.assertEqual(
                self.tc_slugs[slug],
                expected,
                msg=self.parameters.MSG_DOC_KIND_SLUG,
                abort_on_fail=False,
            )

    def bud_link_counts_include_suspect_links_both_ways(self):
        self.print_variables({"counts": self.tc_links})
        self.assertEqual(
            self.tc_links,
            self.parameters.DOC_KIND_LINK_COUNTS,
            msg=self.parameters.MSG_DOC_KIND_LINKS,
            abort_on_fail=False,
        )
