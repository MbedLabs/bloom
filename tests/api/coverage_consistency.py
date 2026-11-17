"""
* @file     ${tests/api/coverage_consistency.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that coverage is reported the same way everywhere.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the coverage reports.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class CoverageConsistencyBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_state_follows_the_verifying_test_cases(self):
        for what, statuses, state in self.parameters.COVC_STATES:
            self.assertEqual(
                self.bloom.bloom_coverage_status(statuses),
                state,
                msg=self.parameters.MSG_COVC_STATE.format(what=what, state=state),
                abort_on_fail=False,
            )

    def bud_the_percentage_is_rounded_to_one_decimal(self):
        for (covered, total), percent in self.parameters.COVC_PERCENTAGES:
            self.assertEqual(
                self.bloom.bloom_coverage_percent(covered, total),
                percent,
                msg=self.parameters.MSG_COVC_PERCENT.format(
                    covered=covered, total=total, percent=percent
                ),
                abort_on_fail=False,
            )

    def bud_every_report_includes_partial_requirements(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.COVC_PREFIXES[0])["id"]
        covered, draft_only, _ = (
            self.bloom.bloom_api_create_requirement(
                self.admin, project, "Verified requirement"
            ).json(),
            self.bloom.bloom_api_create_requirement(
                self.admin, project, "Draft-covered requirement"
            ).json(),
            self.bloom.bloom_api_create_requirement(
                self.admin, project, "Untested requirement"
            ).json(),
        )
        approved, draft = (
            self.bloom.bloom_api_add_test_case(
                self.admin, project, "Approved test case", status="Draft"
            ).body["id"],
            self.bloom.bloom_api_add_test_case(
                self.admin, project, "Draft test case", status="Draft"
            ).body["id"],
        )
        self.bloom.bloom_api_verify(self.admin, project, approved, covered["id"])
        self.bloom.bloom_api_verify(self.admin, project, draft, draft_only["id"])
        self.bloom.bloom_api_approve_test_case(self.admin, approved)
        gaps = self.bloom.bloom_api_call(
            "GET", f"/api/traceability/coverage-gaps/{project}", self.admin
        ).body
        self.print_variables({"gaps": gaps})
        self.assertEqual(
            (
                gaps["total_requirements"],
                gaps["covered"],
                gaps["partial"],
                gaps["uncovered"],
                gaps["coverage_percent"],
            ),
            (3, 1, 1, 1, 66.7),
            msg=values.MSG_COVC_GAPS,
            abort_on_fail=False,
        )
        self.bloom.bloom_clear_dashboard_cache()
        dashboard = self.bloom.bloom_api_call("GET", "/api/dashboard/stats", self.admin).body
        entry = next(item for item in dashboard["projects"] if item["id"] == project)
        card = self.bloom.bloom_api_call("GET", f"/api/projects/{project}", self.admin).body
        self.assertEqual(
            (
                entry["uncovered_requirement_count"],
                card["coverage_percent"],
                card["uncovered_requirement_count"],
            ),
            (gaps["uncovered"], gaps["coverage_percent"], gaps["uncovered"]),
            msg=values.MSG_COVC_SAME,
            abort_on_fail=False,
        )
        matrix = self.bloom.bloom_api_call(
            "GET", "/api/traceability", self.admin, params={"project_id": project}
        ).body["items"]
        states = {item["requirement"]["req_id"]: item["coverage_status"] for item in matrix}
        self.assertEqual(
            (states[covered["req_id"]], states[draft_only["req_id"]]),
            ("Covered", "Partial"),
            msg=values.MSG_COVC_MATRIX,
            abort_on_fail=False,
        )

    def bud_a_draft_test_case_counts_on_the_project_card(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.COVC_PREFIXES[1])["id"]
        requirement = self.bloom.bloom_api_create_requirement(
            self.admin, project, "Only draft coverage"
        ).json()
        self.bloom.bloom_api_verify(
            self.admin,
            project,
            self.bloom.bloom_api_add_test_case(self.admin, project, "Draft", status="Draft").body[
                "id"
            ],
            requirement["id"],
        )
        card, gaps = (
            self.bloom.bloom_api_call("GET", f"/api/projects/{project}", self.admin).body,
            self.bloom.bloom_api_call(
                "GET", f"/api/traceability/coverage-gaps/{project}", self.admin
            ).body,
        )
        self.assertEqual(
            (
                card["coverage_percent"],
                card["uncovered_requirement_count"],
                gaps["partial"],
                gaps["coverage_percent"],
            ),
            (100.0, 0, 1, 100.0),
            msg=values.MSG_COVC_DRAFT,
            abort_on_fail=False,
        )

    def bud_one_test_case_covers_every_requirement_it_verifies(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.COVC_PREFIXES[2])["id"]
        requirements = [
            self.bloom.bloom_api_create_requirement(
                self.admin, project, f"Requirement {number}"
            ).json()
            for number in range(4)
        ]
        test_case = self.bloom.bloom_api_add_test_case(
            self.admin, project, "Verifies three", status="Draft"
        ).body["id"]
        for requirement in requirements[:3]:
            self.bloom.bloom_api_verify(self.admin, project, test_case, requirement["id"])
        self.bloom.bloom_api_approve_test_case(self.admin, test_case)
        card = self.bloom.bloom_api_call("GET", f"/api/projects/{project}", self.admin).body
        self.assertEqual(
            (
                card["requirement_count"],
                card["test_case_count"],
                card["coverage_percent"],
                card["uncovered_requirement_count"],
            ),
            (4, 1, 75.0, 1),
            msg=values.MSG_COVC_FAN_OUT,
            abort_on_fail=False,
        )

    def bud_a_gap_names_its_type_only(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.COVC_PREFIXES[3])["id"]
        self.bloom.bloom_api_create_requirement(self.admin, project, "Bare requirement").json()
        gaps = self.bloom.bloom_api_call(
            "GET", f"/api/traceability/coverage-gaps/{project}", self.admin
        ).body["gaps"]
        self.print_variables({"gaps": gaps})
        self.assertEqual(
            (
                len(gaps) > 0,
                any("missing_link_types" in gap for gap in gaps),
                all(gap["gap_type"] in {"no_test_cases", "all_draft"} for gap in gaps),
            ),
            (True, False, True),
            msg=values.MSG_COVC_GAP_SHAPE,
            abort_on_fail=False,
        )
