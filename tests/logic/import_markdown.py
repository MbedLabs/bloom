"""
* @file     ${tests/logic/import_markdown.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Markdown import: parameters, name collisions and artefacts.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the Markdown import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImportMarkdownBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_collision_blocks_the_import_409(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        _, refusal = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_DOCUMENT
        )
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (refusal[0], refusal[1]["collisions"]),
            (values.STATUS_CONFLICT, values.MDI_COLLISION),
            msg=values.MSG_MDI_BLOCKED,
            abort_on_fail=False,
        )
        self.assertEqual(
            (
                self.bloom.bloom_count_artefacts("Requirement"),
                len(self.bloom.bloom_project_variables()),
            ),
            (0, 1),
            msg=values.MSG_MDI_NOTHING,
            abort_on_fail=False,
        )

    def bud_keeping_the_existing_value_imports_the_rest(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        result, _ = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_DOCUMENT, values.MDI_KEEP
        )
        self.assertEqual(
            (result.parameters_created, result.parameter_collisions, result.parameters_renamed),
            (1, ["BOOT_MS"], {}),
            msg=values.MSG_MDI_KEEP,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_project_variables(),
            {"BOOT_MS": "old", "NEW_ONE": "hello"},
            msg=values.MSG_MDI_KEEP_VALUES,
            abort_on_fail=False,
        )
        requirement = self.bloom.bloom_artefact_titled("Requirement", "Fast boot")
        design = self.bloom.bloom_artefact_titled("DesignItem", "Boot design")
        self.assertEqual(
            (
                {section.title: section.type_code for section in result.sections},
                result.artefacts_created,
                requirement.req_id.startswith("PRJ-REQ-"),
                requirement.description,
                self.bloom.bloom_rich_content_parts(design.content_json)[2],
            ),
            (
                {"Fast boot": "REQ", "Boot design": "DES"},
                2,
                True,
                "Boot within {{BOOT_MS}} ms",
                [("NEW_ONE", "{{")],
            ),
            msg=values.MSG_MDI_ARTEFACTS,
            abort_on_fail=False,
        )
        notes = self.bloom.bloom_notification_bodies()
        self.assertEqual(
            (result.notifications_created, any("Check the necessity" in note for note in notes)),
            (2, True),
            msg=values.MSG_MDI_NOTES,
            abort_on_fail=False,
        )

    def bud_importing_under_a_new_name_renames_every_reference(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        result, _ = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_TWICE, values.MDI_RENAME
        )
        self.assertEqual(
            (result.parameters_renamed, result.parameter_collisions, result.parameters_created),
            ({"BOOT_MS": "BOOT_MS_V2"}, [], 2),
            msg=values.MSG_MDI_RENAME,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_project_variables(),
            {"BOOT_MS": "old", "BOOT_MS_V2": "500", "NEW_ONE": "hello"},
            msg=values.MSG_MDI_RENAME_VALUES,
            abort_on_fail=False,
        )
        requirement = self.bloom.bloom_artefact_titled("Requirement", "Fast boot")
        design = self.bloom.bloom_artefact_titled("DesignItem", "Boot design")
        self.assertEqual(
            (
                requirement.description,
                ("BOOT_MS_V2", "{{")
                in self.bloom.bloom_rich_content_parts(design.content_json)[2],
            ),
            ("Boot within {{BOOT_MS_V2}} ms", True),
            msg=values.MSG_MDI_RENAME_TEXT,
            abort_on_fail=False,
        )

    def bud_a_name_collides_with_a_parameter_of_either_kind(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        self.bloom.bloom_add_project_variable(records.project, "parameter", "LIMIT", "9")
        _, refusal = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_LIMIT
        )
        self.assertEqual(
            refusal[1]["collisions"][0]["existing_value"],
            "9",
            msg=values.MSG_MDI_EITHER_KIND,
            abort_on_fail=False,
        )

    def bud_wrong_collision_actions_are_refused_422(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        for what, actions, phrase in values.MDI_REFUSED_ACTIONS:
            _, refusal = self.bloom.bloom_import_markdown(
                records.project, records.admin, values.MDI_DOCUMENT, actions
            )
            self.assertEqual(
                (refusal[0], phrase in refusal[1]),
                (values.STATUS_UNPROCESSABLE, True),
                msg=values.MSG_MDI_REFUSED.format(what=what),
                abort_on_fail=False,
            )
        _, broken = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_DOCUMENT, raw_actions="{not json"
        )
        self.assertEqual(
            ("not valid JSON" in broken[1], self.bloom.bloom_count_artefacts("Requirement")),
            (True, 0),
            msg=values.MSG_MDI_BROKEN,
            abort_on_fail=False,
        )

    def bud_an_import_without_a_collision_creates_every_parameter(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        result, _ = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_FRESH
        )
        self.assertEqual(
            (result.parameters_created, result.parameter_collisions),
            (2, []),
            msg=values.MSG_MDI_FRESH,
            abort_on_fail=False,
        )

    def bud_renaming_rewrites_the_declaration_and_the_reference(self):
        self.assertEqual(
            self.bloom.bloom_rename_parameters(self.parameters.MDI_RENAME_TEXT, {"x": "X2"}),
            self.parameters.MDI_RENAMED_TEXT,
            msg=self.parameters.MSG_MDI_REWRITE,
            abort_on_fail=False,
        )

    def bud_a_test_case_is_imported_with_its_step_rows(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        result, _ = self.bloom.bloom_import_markdown(
            records.project, records.admin, values.MDI_RELAY_TEST_CASE
        )
        case = self.bloom.bloom_test_case_titled("Relay boot")
        self.assertEqual(
            (
                result.artefacts_created,
                case.tc_id.startswith("PRJ-TC-"),
                self.bloom.bloom_rich_content_parts(case.content_json)[3],
                [
                    (row["row_type"], row["description"], row["expected_result"])
                    for row in case.steps
                ],
            ),
            (1, True, "Checks the relay-driven boot.", values.MDI_STEP_ROWS),
            msg=values.MSG_MDI_RELAY_TEST_CASE,
            abort_on_fail=False,
        )

    def bud_the_import_needs_the_permission_on_every_type_403(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        values = self.parameters
        author = self.bloom.bloom_add_requirement_importer(records.project)
        _, refusal = self.bloom.bloom_import_markdown(
            records.project, author, values.MDI_DOCUMENT, values.MDI_KEEP
        )
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (
                refusal,
                self.bloom.bloom_count_artefacts("Requirement"),
                self.bloom.bloom_count_artefacts("DesignItem"),
            ),
            ((values.STATUS_FORBIDDEN, "Missing permission: import on DES."), 0, 0),
            msg=values.MSG_MDI_PERMISSION,
            abort_on_fail=False,
        )
