"""
* @file     ${tests/api/sync_results_names_the_campaign.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a result sync names the campaigns the results reached.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the campaigns named by a result sync.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class SyncResultsNamesTheCampaignBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_sync_names_the_campaign_reached(self):
        made = self.bloom.bloom_api_add_campaign_with_one_case(
            self.admin, self.parameters.SYNC_PREFIXES[0]
        )
        synced = self.bloom.bloom_api_sync_results(
            None, [{"tc_id": made.case["tc_id"], "status": "Passed"}]
        ).body
        self.print_variables({"synced": synced})
        named = synced["campaigns"][0] if synced["campaigns"] else {}
        link = f"/projects/{made.project['prefix']}/docs/campaigns/{made.campaign['campaign_id']}"
        self.assertEqual(
            (
                synced["updated"],
                [entry["campaign_id"] for entry in synced["campaigns"]],
                named.get("id"),
                named.get("name"),
                named.get("url", "").endswith(link),
            ),
            (1, [made.campaign["campaign_id"]], made.campaign["id"], made.campaign["name"], True),
            msg=self.parameters.MSG_SYNC_NAMED,
            abort_on_fail=False,
        )

    def bud_a_case_in_no_campaign_names_none(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.SYNC_PREFIXES[1])
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        synced = self.bloom.bloom_api_sync_results(
            None, [{"tc_id": case["tc_id"], "status": "Passed"}]
        ).body
        self.assertEqual(
            (synced["updated"], synced["campaigns"]),
            (1, []),
            msg=self.parameters.MSG_SYNC_NO_CAMPAIGN,
            abort_on_fail=False,
        )

    def bud_an_unmatched_id_names_no_campaign(self):
        self.bloom.bloom_api_add_campaign_with_one_case(
            self.admin, self.parameters.SYNC_PREFIXES[2]
        )
        synced = self.bloom.bloom_api_sync_results(
            None, [{"tc_id": "XYZ-TC-404", "status": "Passed"}]
        ).body
        self.assertEqual(
            (synced["updated"], synced["campaigns"]),
            (0, []),
            msg=self.parameters.MSG_SYNC_UNMATCHED,
            abort_on_fail=False,
        )

    def bud_results_reaching_two_campaigns_name_both(self):
        first = self.bloom.bloom_api_add_campaign_with_one_case(
            self.admin, self.parameters.SYNC_PREFIXES[3]
        )
        second = self.bloom.bloom_api_add_campaign_with_one_case(
            self.admin, self.parameters.SYNC_PREFIXES[4]
        )
        results = [
            {"tc_id": first.case["tc_id"], "status": "Passed"},
            {"tc_id": second.case["tc_id"], "status": "Failed"},
        ]
        synced = self.bloom.bloom_api_sync_results(None, results).body
        self.assertEqual(
            (synced["updated"], sorted(entry["campaign_id"] for entry in synced["campaigns"])),
            (2, sorted([first.campaign["campaign_id"], second.campaign["campaign_id"]])),
            msg=self.parameters.MSG_SYNC_BOTH,
            abort_on_fail=False,
        )
