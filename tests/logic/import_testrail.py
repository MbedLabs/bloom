"""
* @file     ${tests/logic/import_testrail.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the TestRail import: cases, suites, requirement links and re-import.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the TestRail import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImportTestrailBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_an_xml_import_creates_cases_a_suite_and_links(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        values = self.parameters
        result, _ = self.bloom.bloom_import_testrail(project, values.TRL_SUITE_XML)
        self.print_variables(
            {
                "created, updated, skipped, links, suites": (
                    result.created,
                    result.updated,
                    result.skipped,
                    result.links_created,
                    result.suites_created,
                )
            }
        )
        self.assertEqual(
            (
                result.created,
                result.updated,
                result.skipped,
                result.links_created,
                len(result.suites_created),
            ),
            (2, 0, 0, 1, 1),
            msg=values.MSG_TRI_COUNTS,
            abort_on_fail=False,
        )
        cold = self.bloom.bloom_test_case_titled("Cold boot")
        self.assertEqual(
            (
                cold.source_ref,
                cold.status,
                cold.reviewer_id,
                cold.approver_id,
                cold.preconditions,
                [r["row_type"] for r in cold.steps],
                cold.description,
            ),
            (
                "testrail:C7",
                "Draft",
                None,
                None,
                "Relay open\n\nSerial console attached",
                ["precondition", "precondition", "step", "step"],
                values.TRI_COLD_DESCRIPTION,
            ),
            msg=values.MSG_TRI_COLD,
            abort_on_fail=False,
        )
        links = self.bloom.bloom_list_artefact_links()
        self.assertEqual(
            [(link.source_type, link.source_id, link.target_type, link.role) for link in links],
            [("TC", cold.id, "REQ", "verifies")],
            msg=values.MSG_TRI_LINK,
            abort_on_fail=False,
        )
        suites = self.bloom.bloom_list_suites()
        self.assertEqual(
            ([(s.name, s.suite_id) for s in suites], len(self.bloom.bloom_list_suite_items())),
            ([("Boot", result.suites_created[0])], 2),
            msg=values.MSG_TRI_SUITE,
            abort_on_fail=False,
        )

    def bud_a_reimport_updates_instead_of_duplicating(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        self.bloom.bloom_import_testrail(project, self.parameters.TRL_SUITE_XML)
        again, _ = self.bloom.bloom_import_testrail(project, self.parameters.TRL_SUITE_XML)
        self.assertEqual(
            (
                again.created,
                again.updated,
                again.suites_created,
                again.links_created,
                len(self.bloom.bloom_list_test_cases()),
                len(self.bloom.bloom_list_suite_items()),
                len(self.bloom.bloom_list_artefact_links()),
            ),
            (0, 2, [], 0, 2, 2, 1),
            msg=self.parameters.MSG_TRI_REIMPORT,
            abort_on_fail=False,
        )

    def bud_a_csv_import_creates_cases_links_and_a_suite(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        result, _ = self.bloom.bloom_import_testrail(
            project, self.parameters.TRL_SEPARATED_CSV, "csv"
        )
        self.assertEqual(
            (
                result.created,
                result.links_created,
                sorted(s.name for s in self.bloom.bloom_list_suites()),
            ),
            (2, 1, ["Firmware"]),
            msg=self.parameters.MSG_TRI_CSV,
            abort_on_fail=False,
        )

    def bud_a_csv_import_reads_through_a_column_mapping(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        result, _ = self.bloom.bloom_import_testrail(
            project, self.parameters.TRI_MAPPED_CSV, "csv", self.parameters.TRI_MAPPING
        )
        cases = self.bloom.bloom_list_test_cases()
        self.assertEqual(
            (
                result.created,
                [[(r["description"], r["expected_result"]) for r in case.steps] for case in cases],
            ),
            (1, [[("Close relay", "Closed")]]),
            msg=self.parameters.MSG_TRI_MAPPING,
            abort_on_fail=False,
        )

    def bud_unreadable_imports_are_refused_422(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        _, bad_mapping = self.bloom.bloom_import_testrail(
            project, self.parameters.TRL_SEPARATED_CSV, "csv", "{not json"
        )
        _, bad_file = self.bloom.bloom_import_testrail(project, b"<cases/>")
        _, no_title = self.bloom.bloom_import_testrail(project, b"Name\nx\n", "csv")
        self.print_variables({"refusals": (bad_mapping, bad_file, no_title)})
        self.assertEqual(
            (
                bad_mapping[0],
                bad_file[0],
                "no <suite>" in bad_file[1],
                "no Title column" in no_title[1],
            ),
            (
                self.parameters.STATUS_UNPROCESSABLE,
                self.parameters.STATUS_UNPROCESSABLE,
                True,
                True,
            ),
            msg=self.parameters.MSG_TRI_ERRORS,
            abort_on_fail=False,
        )

    def bud_a_case_without_a_title_is_skipped(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        result, _ = self.bloom.bloom_import_testrail(project, self.parameters.TRI_NO_TITLE_XML)
        self.assertEqual(
            (result.created, result.skipped, result.errors),
            (0, 1, ["case C1: missing title"]),
            msg=self.parameters.MSG_TRI_NO_TITLE,
            abort_on_fail=False,
        )

    def bud_the_column_preview_lists_the_header(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        preview = self.bloom.bloom_testrail_columns(project, self.parameters.TRL_SEPARATED_CSV)
        self.assertEqual(
            (preview.columns[:2], preview.detected["section_hierarchy"]),
            (["ID", "Title"], "Section Hierarchy"),
            msg=self.parameters.MSG_TRI_PREVIEW,
            abort_on_fail=False,
        )

    def bud_lookups_do_not_grow_with_the_number_of_cases(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        exports = [
            self.bloom.bloom_testrail_export("One", 100, 1),
            self.bloom.bloom_testrail_export("Twenty", 200, 20),
        ]
        (_, twenty), (one_lookups, twenty_lookups) = self.bloom.bloom_count_import_lookups(
            project, exports
        )
        self.print_variables({"lookups for one case": one_lookups, "for twenty": twenty_lookups})
        self.assertEqual(
            (twenty.created, twenty.links_created, twenty_lookups),
            (20, 20, one_lookups),
            msg=self.parameters.MSG_TRI_LOOKUPS,
            abort_on_fail=False,
        )

    def bud_an_import_with_a_removed_link_role_is_refused(self):
        self.bloom.bloom_new_database()
        project = self.bloom.bloom_seed_testrail_project()
        _, refusal = self.bloom.bloom_import_testrail(
            project, self.parameters.TRL_SUITE_XML, without_link_rules=True
        )
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (
                refusal[0],
                "C7" in refusal[1],
                "verifies" in refusal[1],
                self.bloom.bloom_list_test_cases(),
                self.bloom.bloom_list_artefact_links(),
            ),
            (self.parameters.STATUS_UNPROCESSABLE, True, True, [], []),
            msg=self.parameters.MSG_TRI_ROLE,
            abort_on_fail=False,
        )
