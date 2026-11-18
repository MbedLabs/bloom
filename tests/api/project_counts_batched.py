"""
* @file     ${tests/api/project_counts_batched.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the counts in the project list against the project detail.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project counts.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectCountsBatchedBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_listed_counts_match_the_project_detail(self):
        values = self.parameters
        busy = self.bloom.bloom_api_new_project(self.admin, values.PCB_PREFIXES[0])["id"]
        empty = self.bloom.bloom_api_new_project(self.admin, values.PCB_PREFIXES[1])["id"]
        self.bloom.bloom_api_add_requirements(self.admin, busy, 3)
        listed = {
            project["id"]: project
            for project in self.bloom.bloom_api_call("GET", "/api/projects", self.admin).body
        }
        for name, project_id in (("busy", busy), ("empty", empty)):
            detail = self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project_id}", self.admin
            ).body
            for key in values.PCB_COUNT_KEYS:
                self.assertEqual(
                    listed[project_id][key],
                    detail[key],
                    msg=values.MSG_PCB_SAME.format(key=key, project=name),
                    abort_on_fail=False,
                    method="GET",
                    endpoint="/api/projects",
                )
        self.assertEqual(
            (listed[busy]["requirement_count"], listed[empty]["requirement_count"]),
            (3, 0),
            msg=values.MSG_PCB_COUNTS,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects",
        )

    def bud_counts_are_separate_per_project(self):
        values = self.parameters
        one = self.bloom.bloom_api_new_project(self.admin, values.PCB_PREFIXES[2])["id"]
        two = self.bloom.bloom_api_new_project(self.admin, values.PCB_PREFIXES[3])["id"]
        self.bloom.bloom_api_add_requirements(self.admin, one, 1)
        listed = {
            project["id"]: project
            for project in self.bloom.bloom_api_call("GET", "/api/projects", self.admin).body
        }
        self.assertEqual(
            (listed[one]["requirement_count"], listed[two]["requirement_count"]),
            (1, 0),
            msg=values.MSG_PCB_ISOLATED,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects",
        )

    def bud_the_list_does_not_grow_by_a_statement_per_project(self):
        values = self.parameters
        self.bloom.bloom_api_new_project(self.admin, values.PCB_PREFIXES[4])
        _, before = self.bloom.bloom_api_count_statements("GET", "/api/projects", self.admin)
        for prefix in values.PCB_PREFIXES[5:]:
            self.bloom.bloom_api_new_project(self.admin, prefix)
        _, after = self.bloom.bloom_api_count_statements("GET", "/api/projects", self.admin)
        self.print_variables({"statements before": before, "after four more projects": after})
        self.assertTrue(
            after - before <= 2,
            msg=values.MSG_PCB_SCALE,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/projects",
        )
