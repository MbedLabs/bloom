"""
* @file     ${tests/pg/campaign_public_id_duplicates.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the public ID migration on databases holding duplicate public IDs.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the refused public ID migration.
"""

from budtestlibrary import parameterized

import tests.parameters as params
from tests.bloom_test_base import BloomTestCase


class CampaignPublicIdDuplicatesBase(BloomTestCase):

    @parameterized(params.PUBLIC_ID_DUPLICATE_CASES)
    def bud_upgrade_stops_on_duplicate_public_ids(self, index):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        suites, campaigns, column = self.parameters.PUBLIC_ID_DUPLICATES[index]
        code, output, revision = self.tc_refusals[index]
        self.print_variables(
            {"suites": suites, "campaigns": campaigns, "exit code": code, "revision": revision}
        )
        self.assertTrue(code != 0, msg=self.parameters.MSG_DUPLICATES_REFUSED, abort_on_fail=False)
        self.assertIn(
            self.parameters.PUBLIC_ID_DUPLICATE_MESSAGE.format(column=column),
            output,
            msg=self.parameters.MSG_DUPLICATES_NAMED,
            abort_on_fail=False,
        )
        self.assertEqual(
            revision,
            self.parameters.PUBLIC_ID_BEFORE,
            msg=self.parameters.MSG_DUPLICATES_REVISION,
            abort_on_fail=False,
        )
