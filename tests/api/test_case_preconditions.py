"""
* @file     ${tests/api/test_case_preconditions.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that the test case routes store every precondition as a precondition row.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     Base class containing the bud methods of the test case rows and preconditions.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TestCasePreconditionsBase(BloomTestCase):

    interface = BloomApiInterface

    def _create(self, title, steps=None, preconditions=None):
        body = {"project_id": self.project["id"], "title": title}
        if steps is not None:
            body["steps"] = steps
        if preconditions is not None:
            body["preconditions"] = preconditions
        return self.bloom.bloom_api_call("POST", "/api/test-cases", self.admin, json=body)

    def _stored(self, case_id):
        return self.bloom.bloom_api_call("GET", f"/api/test-cases/{case_id}", self.admin).body

    def _rows(self, case):
        return [
            (
                row.get("row_type"),
                row.get("description"),
                row.get("expected_result"),
                row.get("indent_level"),
            )
            for row in (case or {}).get("steps") or []
        ]

    def _check_rows(self, title, steps, expected, message, preconditions=None):
        values = self.parameters
        answer = self._create(title, steps, preconditions)
        case = self._stored(answer.body["id"]) if answer.status == values.STATUS_CREATED else None
        found = (answer.status, self._rows(case), (case or {}).get("preconditions"))
        self.print_variables({"status, rows, preconditions": found})
        self.assertEqual(
            found, (values.STATUS_CREATED, expected, None), msg=message, abort_on_fail=False
        )
        return case

    def bud_a_capitalised_precondition_stays_a_precondition(self):
        values = self.parameters
        self._check_rows(
            "Capitalised types",
            values.PRE_CAPITALISED,
            values.PRE_ROWS_CAPITALISED,
            values.MSG_PRE_CAPITALISED,
        )

    def bud_every_written_form_of_a_type_is_read(self):
        values = self.parameters
        self._check_rows(
            "Labelled types", values.PRE_LABELLED, values.PRE_ROWS_LABELLED, values.MSG_PRE_LABELLED
        )

    def bud_a_row_without_a_type_is_a_step(self):
        values = self.parameters
        self._check_rows(
            "Untyped row", values.PRE_UNTYPED, values.PRE_ROWS_ONE_STEP, values.MSG_PRE_UNTYPED
        )

    def bud_older_field_names_are_read(self):
        values = self.parameters
        self._check_rows(
            "Older names", values.PRE_OLD_NAMES, values.PRE_ROWS_ONE_STEP, values.MSG_PRE_OLD_NAMES
        )

    def bud_a_row_takes_its_type_from_its_label(self):
        values = self.parameters
        self._check_rows(
            "Typed by label", values.PRE_BY_LABEL, values.PRE_ROWS_BY_LABEL, values.MSG_PRE_BY_LABEL
        )

    def bud_the_preconditions_text_becomes_rows(self):
        values = self.parameters
        self._check_rows(
            "Preconditions as text",
            values.PRE_ONE_STEP,
            values.PRE_ROWS_FROM_TEXT,
            values.MSG_PRE_TEXT,
            preconditions=values.PRE_TEXT,
        )

    def bud_a_precondition_line_is_not_added_twice(self):
        values = self.parameters
        self._check_rows(
            "Preconditions in both",
            values.PRE_CAPITALISED,
            values.PRE_ROWS_CAPITALISED,
            values.MSG_PRE_TEXT_TWICE,
            preconditions=values.PRE_ACCOUNT,
        )

    def bud_an_unknown_row_type_is_refused_422(self):
        values = self.parameters
        before = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", self.admin, params={"project_id": self.project["id"]}
        ).body["total"]
        answer = self._create("Unknown type", values.PRE_UNKNOWN)
        detail = str(answer.body.get("detail") if isinstance(answer.body, dict) else answer.body)
        after = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", self.admin, params={"project_id": self.project["id"]}
        ).body["total"]
        found = (
            answer.status,
            "2" in detail and "setup" in detail,
            all(kind in detail for kind in values.PRE_ACCEPTED_TYPES),
            after - before,
        )
        self.print_variables({"status, names row, names types, stored": found, "detail": detail})
        self.assertEqual(
            found,
            (values.STATUS_UNPROCESSABLE, True, True, 0),
            msg=values.MSG_PRE_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_every_stored_row_has_the_editor_form(self):
        values = self.parameters
        case = self._stored(self._create("Editor form", values.PRE_LABELLED).body["id"])
        rows = case.get("steps") or []
        found = (
            {tuple(sorted(row)) for row in rows},
            [row.get("label") == values.PRE_LABELS.get(row.get("row_type")) for row in rows],
            len({row.get("id") for row in rows}) == len(rows),
        )
        self.print_variables({"fields, labels, ids unique": found})
        self.assertEqual(
            found,
            ({tuple(values.PRE_ROW_FIELDS)}, [True] * len(rows), True),
            msg=values.MSG_PRE_EDITOR_FORM,
            abort_on_fail=False,
        )

    def bud_an_update_applies_the_same_rules(self):
        values = self.parameters
        case_id = self._create("Updated case", values.PRE_ONE_STEP).body["id"]
        answer = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/test-cases/{case_id}",
            self.admin,
            json={"steps": values.PRE_OLD_NAMES, "preconditions": values.PRE_TEXT},
        )
        case = self._stored(case_id)
        refused = self.bloom.bloom_api_call(
            "PATCH", f"/api/test-cases/{case_id}", self.admin, json={"steps": values.PRE_UNKNOWN}
        )
        found = (answer.status, self._rows(case), case.get("preconditions"), refused.status)
        self.print_variables({"status, rows, preconditions, unknown": found})
        self.assertEqual(
            found,
            (values.STATUS_OK, values.PRE_ROWS_FROM_TEXT, None, values.STATUS_UNPROCESSABLE),
            msg=values.MSG_PRE_UPDATE,
            abort_on_fail=False,
        )
