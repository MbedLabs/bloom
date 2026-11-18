"""
* @file     ${tests/api/dashboard_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the dashboard totals and what an external reader sees in them.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the dashboard.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DashboardHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_dashboard_reports_its_totals(self):
        values = self.parameters
        admin = self.bloom.bloom_start_api_with_admin()
        first = self.bloom.bloom_api_call("GET", "/api/dashboard/stats", admin)
        second = self.bloom.bloom_api_call("GET", "/api/dashboard/stats", admin)
        self.print_variables({"dashboard": first.body})
        self.assertEqual(
            (
                first.status,
                [key in first.body for key in values.DASH_KEYS],
                isinstance(first.body["projects"], list),
                second.status,
                second.body["total_projects"],
            ),
            (
                values.STATUS_OK,
                [True] * len(values.DASH_KEYS),
                True,
                values.STATUS_OK,
                first.body["total_projects"],
            ),
            msg=values.MSG_DASH_SHAPE,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/dashboard/stats",
        )

    def bud_an_external_reader_sees_visible_records_of_allowed_types(self):
        values = self.parameters
        for types, allowed, (requirements, test_cases, campaigns, uncovered) in values.DASH_CASES:
            reader = self.bloom.bloom_new_external_dashboard_reader(allowed)
            stats = self.bloom.bloom_api_call("GET", "/api/dashboard/stats", reader)
            self.print_variables({types: stats.body})
            body = stats.body
            self.assertEqual(
                (
                    stats.status,
                    body["total_requirements"],
                    body["total_test_cases"],
                    body["total_campaigns"],
                    body["uncovered_requirements"],
                ),
                (values.STATUS_OK, requirements, test_cases, campaigns, uncovered),
                msg=values.MSG_DASH_TOTALS.format(types=types),
                abort_on_fail=False,
                method="GET",
                endpoint="/api/dashboard/stats",
            )
            row = body["projects"][0]
            listed = self.bloom.bloom_api_call("GET", "/api/projects", reader).body[0]
            self.assertEqual(
                (
                    row["uncovered_requirement_count"],
                    (row["requirement_count"], row["test_case_count"]),
                    (
                        listed["requirement_count"],
                        listed["test_case_count"],
                        listed["campaign_count"],
                    ),
                ),
                (uncovered, (requirements, test_cases), (requirements, test_cases, campaigns)),
                msg=values.MSG_DASH_PROJECT.format(types=types),
                abort_on_fail=False,
                method="GET",
                endpoint="/api/projects",
            )
