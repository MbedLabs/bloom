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
        normalized = {
            value: self.bloom.bloom_normalize_document_kind(value)
            for value, _ in self.parameters.DOC_KIND_LEGACY
        }
        for value, expected in self.parameters.DOC_KIND_LEGACY:
            self.print_variables({"stored": value, "kind": normalized[value]})
            self.assertEqual(
                normalized[value],
                expected,
                msg=self.parameters.MSG_DOC_KIND_LEGACY,
                abort_on_fail=False,
            )

    def bud_public_api_accepts_only_canonical_kinds(self):
        required = {
            value: self.bloom.bloom_require_document_kind(value)
            for value in self.parameters.DOC_KIND_ACCEPTED + self.parameters.DOC_KIND_REFUSED
        }
        for value in self.parameters.DOC_KIND_ACCEPTED:
            self.print_variables({"kind": value, "answer": vars(required[value])})
            self.assertEqual(
                required[value].kind,
                value,
                msg=self.parameters.MSG_DOC_KIND_ACCEPTED,
                abort_on_fail=False,
            )
        for value in self.parameters.DOC_KIND_REFUSED:
            answer = required[value]
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
        slugs = {
            slug: self.bloom.bloom_document_kind_from_slug(slug)
            for slug, _ in self.parameters.DOC_KIND_SLUGS
        }
        for slug, expected in self.parameters.DOC_KIND_SLUGS:
            self.print_variables({"slug": slug, "kind": slugs[slug]})
            self.assertEqual(
                slugs[slug],
                expected,
                msg=self.parameters.MSG_DOC_KIND_SLUG,
                abort_on_fail=False,
            )

    def bud_link_counts_include_suspect_links_both_ways(self):
        links = self.bloom.bloom_count_links(
            self.parameters.DOC_KIND_LINK_PROJECT,
            self.parameters.DOC_KIND_LINK_TYPE,
            self.parameters.DOC_KIND_INCOMING,
            self.parameters.DOC_KIND_OUTGOING,
        )
        self.print_variables({"counts": links})
        self.assertEqual(
            links,
            self.parameters.DOC_KIND_LINK_COUNTS,
            msg=self.parameters.MSG_DOC_KIND_LINKS,
            abort_on_fail=False,
        )
