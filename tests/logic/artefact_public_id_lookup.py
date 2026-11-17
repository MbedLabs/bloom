"""
* @file     ${tests/logic/artefact_public_id_lookup.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests addressing artefacts by public id as well as database id.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the public id lookup.
"""

import json

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactPublicIdLookupBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_resolves_by_public_id(self):
        by_public = self.bloom.bloom_lookup_artefact(
            self.parameters.LOOKUP_TEST_CASE_TYPE,
            self.parameters.LOOKUP_TEST_CASE["tc_id"],
            self.parameters.LOOKUP_TEST_CASE_FIELD,
        )
        self.print_variables(vars(by_public))
        self.assertEqual(
            by_public.public_id,
            self.parameters.LOOKUP_TEST_CASE["tc_id"],
            msg=self.parameters.MSG_LOOKUP_PUBLIC,
            abort_on_fail=False,
        )

    def bud_resolves_by_database_id(self):
        by_database = self.bloom.bloom_lookup_artefact(
            self.parameters.LOOKUP_TEST_CASE_TYPE,
            str(self.test_case_id),
            self.parameters.LOOKUP_TEST_CASE_FIELD,
        )
        self.print_variables({**vars(by_database), "database id": self.test_case_id})
        self.assertEqual(
            by_database.id,
            self.test_case_id,
            msg=self.parameters.MSG_LOOKUP_DATABASE,
            abort_on_fail=False,
        )

    def bud_unknown_public_id_is_not_found(self):
        unknown = self.bloom.bloom_lookup_artefact(
            self.parameters.LOOKUP_TEST_CASE_TYPE,
            self.parameters.LOOKUP_UNKNOWN,
            self.parameters.LOOKUP_TEST_CASE_FIELD,
        )
        self.print_variables(vars(unknown))
        self.assertEqual(
            unknown.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_LOOKUP_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_backlinks_match_by_public_and_database_id(self):
        related_public = self.bloom.bloom_related_artefacts(
            self.parameters.LOOKUP_DEFECT_TYPE, self.parameters.LOOKUP_DEFECT["defect_id"]
        )
        related_database = self.bloom.bloom_related_artefacts(
            self.parameters.LOOKUP_DEFECT_TYPE, str(self.defect_id)
        )
        by_public = json.dumps(related_public, default=str)
        self.print_variables({"by public id": by_public[:200]})
        self.assertEqual(
            related_public,
            related_database,
            msg=self.parameters.MSG_LOOKUP_SAME_BACKLINKS,
            abort_on_fail=False,
        )
        self.assertIn(
            self.parameters.LOOKUP_REQUIREMENT["req_id"],
            by_public,
            msg=self.parameters.MSG_LOOKUP_BACKLINK,
            abort_on_fail=False,
        )
