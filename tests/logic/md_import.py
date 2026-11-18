"""
* @file     ${tests/logic/md_import.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the Markdown import: classification, parameters and collisions.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the Markdown import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class MdImportBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_frontmatter_sets_the_document_type(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_FRONTMATTER)
        section = doc.sections[0]
        self.assertEqual(
            (doc.doc_type, section.type_code, section.title, "Must work." in section.body),
            ("REQ", "REQ", "Login", True),
            msg=self.parameters.MSG_MDI_FRONTMATTER,
            abort_on_fail=False,
        )

    def bud_a_heading_tag_classifies_its_section(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_TAGGED)
        self.assertEqual(
            [(s.type_code, s.title) for s in doc.sections],
            [("REQ", "Boot fast"), ("DES", "Boot design")],
            msg=self.parameters.MSG_MDI_TAGGED,
            abort_on_fail=False,
        )

    def bud_an_unmarked_document_takes_the_default_type(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_UNMARKED, "design")
        self.assertEqual(
            (doc.doc_type, doc.sections[0].type_code),
            ("DES", "DES"),
            msg=self.parameters.MSG_MDI_DEFAULT,
            abort_on_fail=False,
        )

    def bud_parameters_in_a_sentence_become_placeholders(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_WRAPPED)
        self.assertEqual(
            ([(p.name, p.value) for p in doc.parameters], doc.sections[0].body),
            (
                [("BOOT_MS", "500"), ("MAX_TEMP", "85C")],
                "Boot within {{BOOT_MS}} ms of power-on, below {{MAX_TEMP}}.",
            ),
            msg=self.parameters.MSG_MDI_WRAPPED,
            abort_on_fail=False,
        )

    def bud_an_existing_parameter_reference_is_left_alone(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_REFERENCE)
        self.assertEqual(
            (doc.parameters, doc.sections[0].body),
            ([], "Boot within {{BOOT_MS}} ms."),
            msg=self.parameters.MSG_MDI_REFERENCE,
            abort_on_fail=False,
        )

    def bud_a_parameter_in_a_heading_is_replaced(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_HEADING)
        self.assertEqual(
            (doc.sections[0].title, [(p.name, p.value) for p in doc.parameters]),
            ("Boot in {{BOOT_MS}} ms", [("BOOT_MS", "500")]),
            msg=self.parameters.MSG_MDI_HEADING,
            abort_on_fail=False,
        )

    def bud_parameter_collisions_require_action(self):
        collisions = self.bloom.bloom_parameter_collisions(
            [("BOOT_MS", "500"), ("NEW_ONE", "1")], ["boot_ms", "other"]
        )
        self.assertEqual(
            collisions, ["BOOT_MS"], msg=self.parameters.MSG_MDI_COLLISION, abort_on_fail=False
        )

    def bud_test_case_rows_follow_the_step_contract(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_TEST_CASE)
        tc = doc.sections[0]
        rows = [
            (r["row_type"], r["label"], r["indent_level"], r["description"], r["expected_result"])
            for r in tc.steps
        ]
        self.print_variables({"rows": rows})
        self.assertEqual(
            (
                tc.type_code,
                tc.body,
                rows,
                all(r["collapsed"] is False and r["id"] for r in tc.steps),
                [p.name for p in doc.parameters],
            ),
            (
                "TC",
                "Measures the cold boot time of the device under test.",
                self.parameters.MDI_TEST_CASE_ROWS,
                True,
                ["BOOT_CYCLES", "BOOT_BUDGET_MS", "BOOT_TOLERANCE_MS"],
            ),
            msg=self.parameters.MSG_MDI_TEST_CASE,
            abort_on_fail=False,
        )

    def bud_step_lines_outside_a_test_case_stay_text(self):
        doc = self.bloom.bloom_parse_markdown(self.parameters.MDI_STRAY_STEP)
        self.assertEqual(
            (doc.sections[0].steps, doc.sections[0].body),
            ([], "- Step: not a test case row"),
            msg=self.parameters.MSG_MDI_STRAY,
            abort_on_fail=False,
        )
