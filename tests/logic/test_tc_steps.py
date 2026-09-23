"""Step rows survive every export and import: one text form, round-tripped."""

from types import SimpleNamespace

from app.api.export import _test_cases_markdown, _test_cases_xml
from app.api.import_service import _import_rows_from_xml
from app.core.md_import import parse_markdown_document
from app.core.tc_steps import make_row, rows_to_text, text_to_rows

EDITOR_ROWS = [
    make_row("precondition", "device under test powered off through the relay"),
    make_row("loop", "repeat {{BOOT_CYCLES}} times"),
    make_row("step", "switch the relay on", "relay reports closed", indent=1),
    make_row(
        "step",
        "measure the time from relay on\nto the boot banner",
        "within {{BOOT_BUDGET_MS}} ms\n+- {{BOOT_TOLERANCE_MS}} ms",
        indent=1,
    ),
]


def _fields(rows):
    return [
        (r["row_type"], r["label"], r["indent_level"], r["description"], r["expected_result"])
        for r in rows
    ]


def test_editor_rows_round_trip_through_the_text_form():
    text = rows_to_text(EDITOR_ROWS)
    assert text.splitlines()[:3] == [
        "- Pre-Condition: device under test powered off through the relay",
        "- Loop: repeat {{BOOT_CYCLES}} times",
        "  - Step: switch the relay on => relay reports closed",
    ]
    assert _fields(text_to_rows(text)) == _fields(EDITOR_ROWS)


def test_rows_carry_the_editor_contract():
    row = text_to_rows("- Step: a => b")[0]
    assert set(row) == {
        "id",
        "row_type",
        "label",
        "description",
        "expected_result",
        "indent_level",
        "collapsed",
    }
    assert row["collapsed"] is False and row["id"]


def test_older_stored_steps_still_write():
    legacy = [{"action": "Open login", "expected": "Form shown"}, {"step": "Submit"}]
    assert rows_to_text(legacy) == "- Step: Open login => Form shown\n- Step: Submit"


def test_older_numbered_text_still_reads():
    rows = text_to_rows("1. Open => Form\n2) Submit\nplain line")
    assert _fields(rows) == [
        ("step", "Step", 0, "Open", "Form"),
        ("step", "Step", 0, "Submit", ""),
        ("step", "Step", 0, "plain line", ""),
    ]


def test_empty_steps():
    assert text_to_rows("") is None
    assert text_to_rows("   \n ") is None
    assert rows_to_text(None) == ""
    assert rows_to_text([]) == ""


def test_text_before_the_first_row_becomes_a_step():
    rows = text_to_rows("setup note\n- Step: go => done")
    assert _fields(rows) == [
        ("step", "Step", 0, "setup note", ""),
        ("step", "Step", 0, "go", "done"),
    ]


def _case(**overrides):
    base = dict(
        tc_id="ALP-TC-001",
        title="Boot within budget",
        status="Approved",
        visibility="internal",
        preconditions=None,
        steps=EDITOR_ROWS,
        description="Measures the cold boot time.",
        last_execution_status=None,
        created_at=None,
        updated_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


PROJECT = SimpleNamespace(name="Alpha", prefix="ALP")


def test_xml_export_reimports_the_same_rows():
    rows = _import_rows_from_xml(_test_cases_xml(PROJECT, [_case()]))
    assert rows[0]["tc_id"] == "ALP-TC-001"
    assert _fields(text_to_rows(rows[0]["steps"])) == _fields(EDITOR_ROWS)


def test_markdown_export_reimports_as_the_same_test_case():
    doc = parse_markdown_document(_test_cases_markdown(PROJECT, [_case()]))
    assert len(doc.sections) == 1
    section = doc.sections[0]
    assert (section.type_code, section.title) == ("TC", "Boot within budget")
    assert section.body == "Measures the cold boot time."
    assert [
        (r["row_type"], r["indent_level"], r["description"], r["expected_result"])
        for r in section.steps
    ][:3] == [
        ("precondition", 0, "device under test powered off through the relay", ""),
        ("loop", 0, "repeat {{BOOT_CYCLES}} times", ""),
        ("step", 1, "switch the relay on", "relay reports closed"),
    ]


def test_markdown_export_turns_plain_preconditions_into_a_row():
    case = _case(preconditions="relay open", steps=[make_row("step", "close", "banner")])
    doc = parse_markdown_document(_test_cases_markdown(PROJECT, [case]))
    assert [r["row_type"] for r in doc.sections[0].steps] == ["precondition", "step"]
