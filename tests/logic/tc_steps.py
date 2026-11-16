"""
* @file     ${tests/logic/tc_steps.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that test case step rows survive every export and import.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test case steps.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class TcStepsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_editor_rows_round_trip_through_the_text_form(self):
        editor = self.bloom.bloom_editor_rows(self.parameters.TCS_EDITOR_ROWS)
        text = self.bloom.bloom_rows_to_text(editor)
        self.print_variables({"text": text})
        self.assertEqual(
            (
                text.splitlines()[:3],
                self.bloom.bloom_row_fields(self.bloom.bloom_text_to_rows(text)),
            ),
            (self.parameters.TCS_FIRST_LINES, self.bloom.bloom_row_fields(editor)),
            msg=self.parameters.MSG_TCS_TEXT,
            abort_on_fail=False,
        )

    def bud_rows_carry_the_editor_contract(self):
        row = self.bloom.bloom_text_to_rows("- Step: a => b")[0]
        self.assertEqual(
            (sorted(row), row["collapsed"], bool(row["id"])),
            (self.parameters.TCS_ROW_KEYS, False, True),
            msg=self.parameters.MSG_TCS_CONTRACT,
            abort_on_fail=False,
        )

    def bud_older_stored_steps_still_write(self):
        legacy = [{"action": "Open login", "expected": "Form shown"}, {"step": "Submit"}]
        self.assertEqual(
            self.bloom.bloom_rows_to_text(legacy),
            "- Step: Open login => Form shown\n- Step: Submit",
            msg=self.parameters.MSG_TCS_LEGACY_WRITE,
            abort_on_fail=False,
        )

    def bud_older_numbered_text_still_reads(self):
        self.assertEqual(
            self.bloom.bloom_row_fields(
                self.bloom.bloom_text_to_rows("1. Open => Form\n2) Submit\nplain line")
            ),
            [
                ("step", "Step", 0, "Open", "Form"),
                ("step", "Step", 0, "Submit", ""),
                ("step", "Step", 0, "plain line", ""),
            ],
            msg=self.parameters.MSG_TCS_LEGACY_READ,
            abort_on_fail=False,
        )

    def bud_empty_steps_read_and_write_as_nothing(self):
        self.assertEqual(
            (
                self.bloom.bloom_text_to_rows(""),
                self.bloom.bloom_text_to_rows("   \n "),
                self.bloom.bloom_rows_to_text(None),
                self.bloom.bloom_rows_to_text([]),
            ),
            (None, None, "", ""),
            msg=self.parameters.MSG_TCS_EMPTY,
            abort_on_fail=False,
        )

    def bud_text_before_the_first_row_becomes_a_step(self):
        self.assertEqual(
            self.bloom.bloom_row_fields(
                self.bloom.bloom_text_to_rows("setup note\n- Step: go => done")
            ),
            [("step", "Step", 0, "setup note", ""), ("step", "Step", 0, "go", "done")],
            msg=self.parameters.MSG_TCS_LEADING,
            abort_on_fail=False,
        )

    def bud_the_xml_export_reimports_the_same_rows(self):
        editor = self.bloom.bloom_editor_rows(self.parameters.TCS_EDITOR_ROWS)
        reimported = self.bloom.bloom_xml_reimport([self.bloom.bloom_step_case(steps=editor)])
        self.assertEqual(
            (
                reimported[0]["tc_id"],
                self.bloom.bloom_row_fields(self.bloom.bloom_text_to_rows(reimported[0]["steps"])),
            ),
            ("PRJ-TC-001", self.bloom.bloom_row_fields(editor)),
            msg=self.parameters.MSG_TCS_XML,
            abort_on_fail=False,
        )

    def bud_the_markdown_export_reimports_the_same_test_case(self):
        doc = self.bloom.bloom_markdown_reimport(
            [
                self.bloom.bloom_step_case(
                    steps=self.bloom.bloom_editor_rows(self.parameters.TCS_EDITOR_ROWS)
                )
            ]
        )
        section = doc.sections[0]
        self.assertEqual(
            (
                len(doc.sections),
                (section.type_code, section.title),
                section.body,
                [
                    (r["row_type"], r["indent_level"], r["description"], r["expected_result"])
                    for r in section.steps
                ][:3],
            ),
            (
                1,
                ("TC", "Boot within budget"),
                "Measures the cold boot time.",
                [
                    ("precondition", 0, "device under test powered off through the relay", ""),
                    ("loop", 0, "repeat {{BOOT_CYCLES}} times", ""),
                    ("step", 1, "switch the relay on", "relay reports closed"),
                ],
            ),
            msg=self.parameters.MSG_TCS_MARKDOWN,
            abort_on_fail=False,
        )

    def bud_plain_preconditions_become_a_row(self):
        case = self.bloom.bloom_step_case(
            preconditions="relay open",
            steps=self.bloom.bloom_editor_rows([("step", "close", "banner", 0)]),
        )
        doc = self.bloom.bloom_markdown_reimport([case])
        self.assertEqual(
            [r["row_type"] for r in doc.sections[0].steps],
            ["precondition", "step"],
            msg=self.parameters.MSG_TCS_PRECONDITION,
            abort_on_fail=False,
        )
