"""
* @file     ${tests/api/sync_results_names_the_suite.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a result sync names the suites holding the synced test cases.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the suites named by a result sync.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class SyncResultsNamesTheSuiteBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_sync_names_the_suite_holding_the_case(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.SYNS_PREFIXES[0])
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        suite = self.bloom.bloom_api_add_suite(self.admin, project["id"], "Suite", [case])
        synced = self.bloom.bloom_api_sync_results(
            None, [{"tc_id": case["tc_id"], "status": "Passed"}]
        ).body
        self.print_variables({"synced": synced})
        named = synced["suites"][0] if synced["suites"] else {}
        link = f"/projects/{project['prefix']}/docs/test-suites/{suite['suite_id']}"
        self.assertEqual(
            (
                synced["updated"],
                [entry["suite_id"] for entry in synced["suites"]],
                named.get("id"),
                named.get("name"),
                named.get("url", "").endswith(link),
                named.get("matched"),
                named.get("size"),
            ),
            (1, [suite["suite_id"]], suite["id"], suite["name"], True, 1, 1),
            msg=self.parameters.MSG_SYNS_NAMED,
            abort_on_fail=False,
        )

    def bud_each_suite_counts_its_synced_cases(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.SYNS_PREFIXES[1])
        first, second, third = (
            self.bloom.bloom_api_add_test_case(self.admin, project["id"], title).body
            for title in ("First", "Second", "Third")
        )
        executed = self.bloom.bloom_api_add_suite(
            self.admin, project["id"], "Executed", [first, second]
        )
        superset = self.bloom.bloom_api_add_suite(
            self.admin, project["id"], "Superset", [first, second, third]
        )
        results = [
            {"tc_id": first["tc_id"], "status": "Passed"},
            {"tc_id": second["tc_id"], "status": "Failed"},
        ]
        synced = self.bloom.bloom_api_sync_results(None, results).body
        counts = {entry["id"]: (entry["matched"], entry["size"]) for entry in synced["suites"]}
        self.assertEqual(
            counts,
            {executed["id"]: (2, 2), superset["id"]: (2, 3)},
            msg=self.parameters.MSG_SYNS_COUNTS,
            abort_on_fail=False,
        )

    def bud_a_case_in_no_suite_names_none(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.SYNS_PREFIXES[2])
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        synced = self.bloom.bloom_api_sync_results(
            None, [{"tc_id": case["tc_id"], "status": "Passed"}]
        ).body
        self.assertEqual(
            (synced["updated"], synced["suites"]),
            (1, []),
            msg=self.parameters.MSG_SYNS_NO_SUITE,
            abort_on_fail=False,
        )

    def bud_an_unmatched_id_names_no_suite(self):
        project = self.bloom.bloom_api_new_project(self.admin, self.parameters.SYNS_PREFIXES[3])
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        self.bloom.bloom_api_add_suite(self.admin, project["id"], "Suite", [case])
        synced = self.bloom.bloom_api_sync_results(
            None, [{"tc_id": "XYZ-TC-404", "status": "Passed"}]
        ).body
        self.assertEqual(
            (synced["updated"], synced["suites"]),
            (0, []),
            msg=self.parameters.MSG_SYNS_UNMATCHED,
            abort_on_fail=False,
        )
