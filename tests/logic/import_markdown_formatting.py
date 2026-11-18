"""
* @file     ${tests/logic/import_markdown_formatting.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that imported Markdown becomes the editor's rich content and that a declaration sets the kind.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     Base class containing the bud methods of the formatted Markdown import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImportMarkdownFormattingBase(BloomTestCase):

    interface = BloomLogicInterface

    def _import(self, document, actions=None):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_markdown_project()
        return self.bloom.bloom_import_markdown(records.project, records.admin, document, actions)

    def _parts(self, title):
        return self.bloom.bloom_rich_content_parts(self.bloom.bloom_imported_contents().get(title))

    def bud_an_imported_specification_has_rich_content(self):
        values = self.parameters
        self._import(values.MDF_SPECIFICATION)
        nodes, _, _, text = self._parts("Sign-in")
        self.print_variables({"nodes": sorted(map(str, nodes)), "text": text})
        self.assertEqual(
            (values.MDF_SPECIFICATION_NODES <= nodes, text),
            (True, values.MDF_SPECIFICATION_TEXT),
            msg=values.MSG_MDF_SPECIFICATION,
            abort_on_fail=False,
        )

    def bud_every_markdown_element_becomes_its_editor_node(self):
        values = self.parameters
        result, refusal = self._import(values.MDF_EVERY_ELEMENT)
        nodes, marks, _, text = self._parts("Formatted rule")
        sections = (
            {section.title: section.type_code for section in result.sections} if result else refusal
        )
        self.print_variables(
            {
                "sections": sections,
                "missing nodes": sorted(values.MDF_ELEMENT_NODES - nodes),
                "missing marks": sorted(values.MDF_ELEMENT_MARKS - marks),
                "text": text,
            }
        )
        self.assertEqual(
            (
                sections,
                sorted(values.MDF_ELEMENT_NODES - nodes),
                sorted(values.MDF_ELEMENT_MARKS - marks),
                "# not a heading" in text,
            ),
            (values.MDF_EVERY_ELEMENT_SECTIONS, [], [], True),
            msg=values.MSG_MDF_ELEMENTS,
            abort_on_fail=False,
        )

    def bud_a_parameter_reference_becomes_the_parameter_chip(self):
        values = self.parameters
        self._import(values.MDF_PARAMETER_REFERENCE)
        _, _, chips, text = self._parts("Idle timeout")
        self.print_variables({"chips": chips, "text": text})
        self.assertEqual(
            (chips, "{{" in text),
            (values.MDF_PARAMETER_CHIPS, False),
            msg=values.MSG_MDF_CHIPS,
            abort_on_fail=False,
        )

    def bud_a_test_case_keeps_its_rows_and_gets_rich_text(self):
        values = self.parameters
        self._import(values.MDF_TEST_CASE)
        case = self.bloom.bloom_test_case_titled("Relay boot")
        _, marks, _, text = self._parts("Relay boot")
        rows = [
            (row["row_type"], row["description"], row["expected_result"])
            for row in case.steps or []
        ]
        self.print_variables({"rows": rows, "marks": sorted(map(str, marks)), "text": text})
        self.assertEqual(
            (rows, "bold" in marks, text),
            (values.MDI_STEP_ROWS, True, values.MDF_TEST_CASE_TEXT),
            msg=values.MSG_MDF_TEST_CASE,
            abort_on_fail=False,
        )

    def bud_every_type_but_the_defect_holds_rich_content(self):
        values = self.parameters
        self._import(values.MDF_EVERY_TYPE)
        contents = self.bloom.bloom_imported_contents()
        for title in values.MDF_EVERY_TYPE_TITLES:
            _, marks, _, text = self.bloom.bloom_rich_content_parts(contents.get(title))
            self.assertEqual(
                ("bold" in marks, text),
                (True, values.MDF_TYPED_TEXT),
                msg=values.MSG_MDF_EVERY_TYPE.format(title=title),
                abort_on_fail=False,
            )

    def bud_a_declaration_sets_the_kind(self):
        values = self.parameters
        self._import(values.MDF_TWO_KINDS)
        requirement = self.bloom.bloom_artefact_titled("Requirement", "Two kinds")
        kinds = self.bloom.bloom_project_variable_kinds()
        self.print_variables({"kinds": kinds})
        self.assertEqual(
            (kinds, requirement.description if requirement else None),
            (values.MDF_TWO_KINDS_VALUES, values.MDF_TWO_KINDS_TEXT),
            msg=values.MSG_MDF_KINDS,
            abort_on_fail=False,
        )

    def bud_a_declared_variable_collides_like_a_parameter_409(self):
        values = self.parameters
        _, refusal = self._import(values.MDF_VARIABLE_COLLISION)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (refusal[0], refusal[1]["collisions"]) if refusal else None,
            (values.STATUS_CONFLICT, values.MDF_VARIABLE_COLLISION_FOUND),
            msg=values.MSG_MDF_VARIABLE_COLLISION,
            abort_on_fail=False,
        )
