"""
* @file     ${tests/logic/search.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the global search across projects and access.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the global search.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class SearchBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_an_administrator_searches_every_project(self):
        found = self.bloom.bloom_search(self.records.admin, "login")
        types = {(item.type, item.doc_id) for item in found.items}
        self.print_variables({"found": types})
        self.assertTrue(
            self.parameters.SRC_ALL_LOGIN <= types,
            msg=self.parameters.MSG_SRC_ADMIN,
            abort_on_fail=False,
        )

    def bud_an_exact_id_ranks_first(self):
        found = self.bloom.bloom_search(self.records.admin, self.parameters.SRC_EXACT_ID)
        self.assertEqual(
            [item.doc_id for item in found.items][:1],
            [self.parameters.SRC_EXACT_ID],
            msg=self.parameters.MSG_SRC_EXACT,
            abort_on_fail=False,
        )

    def bud_the_project_filter_narrows_the_results(self):
        found = self.bloom.bloom_search(self.records.admin, "login", self.records.beta)
        self.assertEqual(
            {item.project_prefix for item in found.items},
            {"ABC"},
            msg=self.parameters.MSG_SRC_PROJECT,
            abort_on_fail=False,
        )

    def bud_a_member_finds_their_own_project_only(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_search_records()
        self.bloom.bloom_add_internal_member(
            records.alpha, records.member, self.parameters.SRC_EVERYTHING
        )
        found = self.bloom.bloom_search(records.member, "login")
        self.assertEqual(
            {item.project_prefix for item in found.items},
            {"PRJ"},
            msg=self.parameters.MSG_SRC_MEMBER,
            abort_on_fail=False,
        )

    def bud_a_user_without_project_access_finds_nothing(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_search_records()
        found = self.bloom.bloom_search(records.member, "login")
        self.assertEqual(
            (found.total, found.items),
            (0, []),
            msg=self.parameters.MSG_SRC_NO_MEMBERSHIP,
            abort_on_fail=False,
        )

    def bud_an_external_reader_is_limited_by_type_and_visibility(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_search_records()
        self.bloom.bloom_add_external_member(
            records.alpha, records.external, self.parameters.SRC_READER, "customer", ["REQ"]
        )
        found = self.bloom.bloom_search(records.external, "login")
        self.assertEqual(
            {(item.type, item.doc_id) for item in found.items},
            {("REQ", "PRJ-REQ-001")},
            msg=self.parameters.MSG_SRC_EXTERNAL,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_search(records.external, "crypto").total,
            0,
            msg=self.parameters.MSG_SRC_EXTERNAL_INTERNAL,
            abort_on_fail=False,
        )

    def bud_an_external_reader_without_allowed_types_finds_nothing(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_search_records()
        self.bloom.bloom_add_external_member(
            records.alpha, records.external, self.parameters.SRC_READER, "customer", []
        )
        self.assertEqual(
            self.bloom.bloom_search(records.external, "login").total,
            0,
            msg=self.parameters.MSG_SRC_NO_ALLOWLIST,
            abort_on_fail=False,
        )

    def bud_matches_rank_from_exact_id_to_no_match(self):
        for what, query, doc_id, title, rank in self.parameters.SRC_RANKS:
            self.assertEqual(
                self.bloom.bloom_rank_match(query, doc_id, title),
                rank,
                msg=self.parameters.MSG_SRC_RANK.format(what=what, rank=rank),
                abort_on_fail=False,
            )
