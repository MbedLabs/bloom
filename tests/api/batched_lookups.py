"""
* @file     ${tests/api/batched_lookups.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the batched lookups of suites, test cases and document sections.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the batched lookups.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class BatchedLookupsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_campaign_refuses_an_unknown_suite_404(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.BLK_PREFIXES[0])["id"]
        body = {"project_id": project, "name": "C", "suite_ids": [values.BLK_UNKNOWN_SUITE]}
        answer = self.bloom.bloom_api_call("POST", "/api/campaigns", self.admin, json=body)
        self.print_variables({"answer": answer.body})
        self.assertEqual(
            (answer.status, str(values.BLK_UNKNOWN_SUITE) in str(answer.body)),
            (values.STATUS_NOT_FOUND, True),
            msg=values.MSG_BLK_UNKNOWN,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/campaigns",
        )

    def bud_a_campaign_refuses_a_suite_of_another_project_404(self):
        values = self.parameters
        mine = self.bloom.bloom_api_new_project(self.admin, values.BLK_PREFIXES[1])["id"]
        theirs = self.bloom.bloom_api_new_project(self.admin, values.BLK_PREFIXES[2])["id"]
        foreign = self.bloom.bloom_api_add_suite(self.admin, theirs, "Foreign", [])["id"]
        answer = self.bloom.bloom_api_call(
            "POST",
            "/api/campaigns",
            self.admin,
            json={"project_id": mine, "name": "C", "suite_ids": [foreign]},
        )
        self.assertEqual(
            (answer.status, str(foreign) in str(answer.body)),
            (values.STATUS_NOT_FOUND, True),
            msg=values.MSG_BLK_FOREIGN,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/campaigns",
        )

    def bud_a_suite_skips_test_cases_of_another_project(self):
        values = self.parameters
        mine = self.bloom.bloom_api_new_project(self.admin, values.BLK_PREFIXES[3])["id"]
        theirs = self.bloom.bloom_api_new_project(self.admin, values.BLK_PREFIXES[4])["id"]
        ours = self.bloom.bloom_api_add_test_case(self.admin, mine, "Ours").body
        foreign = self.bloom.bloom_api_add_test_case(self.admin, theirs, "Foreign").body
        created = self.bloom.bloom_api_add_suite(
            self.admin, mine, "S", [ours, foreign, {"id": values.BLK_UNKNOWN_SUITE}]
        )
        detail = self.bloom.bloom_api_call(
            "GET", f"/api/test-suites/{created['suite_id']}", self.admin
        )
        self.assertEqual(
            (detail.status, detail.body["total_items"]),
            (values.STATUS_OK, 1),
            msg=values.MSG_BLK_SKIPPED,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/test-suites/{suite_id}",
        )

    def bud_section_counts_are_per_document(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.BLK_PREFIXES[5])["id"]
        path = f"/api/projects/{project}/documents"
        first, second = (
            self.bloom.bloom_api_call(
                "POST", path, self.admin, json={"project_id": project, "title": title}
            ).body["id"]
            for title in ("Doc 0", "Doc 1")
        )
        for number in range(3):
            self.bloom.bloom_api_call(
                "POST",
                f"/api/documents/{first}/sections",
                self.admin,
                json={"title": f"Section {number}", "content": "x"},
            )
        listed = self.bloom.bloom_api_call("GET", path, self.admin).body
        rows = listed["items"] if isinstance(listed, dict) else listed
        counts = {row["id"]: row["section_count"] for row in rows}
        self.assertEqual(
            (counts[first], counts[second]),
            (3, 0),
            msg=values.MSG_BLK_SECTIONS,
            abort_on_fail=False,
            method="GET",
            endpoint=path,
        )
