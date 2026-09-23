"""Markdown import: classification, parameters, and collision detection."""

from app.core.md_import import (
    Parameter,
    parameter_name_collisions,
    parse_markdown_document,
)


def test_frontmatter_sets_doc_type():
    doc = parse_markdown_document("---\ntype: requirement\n---\n# Login\nMust work.")
    assert doc.doc_type == "REQ"
    assert doc.sections[0].type_code == "REQ"
    assert doc.sections[0].title == "Login"
    assert "Must work." in doc.sections[0].body


def test_heading_tag_classifies_per_section():
    text = "## [REQ] Boot fast\nbody a\n## [DES] Boot design\nbody b"
    doc = parse_markdown_document(text)
    assert [(s.type_code, s.title) for s in doc.sections] == [
        ("REQ", "Boot fast"),
        ("DES", "Boot design"),
    ]


def test_default_type_used_when_unmarked():
    doc = parse_markdown_document("# Untagged\nsome text", default_type="design")
    assert doc.doc_type == "DES"
    assert doc.sections[0].type_code == "DES"


def test_wrapped_parameters_in_a_sentence_become_placeholders():
    text = (
        "## [REQ] Boot\n"
        "Boot within {{parameter: BOOT_MS, value: 500}} ms of power-on, "
        "below {{parameter: MAX_TEMP, value: 85C}}.\n"
    )
    doc = parse_markdown_document(text)
    assert [(p.name, p.value) for p in doc.parameters] == [
        ("BOOT_MS", "500"),
        ("MAX_TEMP", "85C"),
    ]
    assert doc.sections[0].body == "Boot within {{BOOT_MS}} ms of power-on, below {{MAX_TEMP}}."


def test_existing_parameter_reference_is_left_alone():
    doc = parse_markdown_document("## [REQ] Boot\nBoot within {{BOOT_MS}} ms.\n")
    assert doc.parameters == []
    assert doc.sections[0].body == "Boot within {{BOOT_MS}} ms."


def test_parameter_in_a_heading_is_replaced():
    doc = parse_markdown_document("## [REQ] Boot in {{parameter: BOOT_MS, value: 500}} ms\n")
    assert doc.sections[0].title == "Boot in {{BOOT_MS}} ms"
    assert [(p.name, p.value) for p in doc.parameters] == [("BOOT_MS", "500")]


def test_parameter_collisions_require_action():
    params = [Parameter("BOOT_MS", "500"), Parameter("NEW_ONE", "1")]
    collisions = parameter_name_collisions(params, existing_names=["boot_ms", "other"])
    assert collisions == ["BOOT_MS"]


def test_test_case_rows_follow_the_step_contract():
    text = (
        "## [TC] Boot within budget\n"
        "Measures the cold boot time of the device under test.\n"
        "- Pre-Condition: device under test powered off through the relay\n"
        "- Loop: repeat {{parameter: BOOT_CYCLES, value: 3}} times\n"
        "  - Step: switch the relay on => relay reports closed\n"
        "  - Step: measure the time from relay on to boot banner => within "
        "{{parameter: BOOT_BUDGET_MS, value: 500}} ms +- "
        "{{parameter: BOOT_TOLERANCE_MS, value: 50}} ms\n"
    )
    doc = parse_markdown_document(text)
    tc = doc.sections[0]
    assert tc.type_code == "TC"
    assert tc.body == "Measures the cold boot time of the device under test."
    assert [
        (r["row_type"], r["label"], r["indent_level"], r["description"], r["expected_result"])
        for r in tc.steps
    ] == [
        ("precondition", "Pre-Condition", 0, "device under test powered off through the relay", ""),
        ("loop", "Loop", 0, "repeat {{BOOT_CYCLES}} times", ""),
        ("step", "Step", 1, "switch the relay on", "relay reports closed"),
        (
            "step",
            "Step",
            1,
            "measure the time from relay on to boot banner",
            "within {{BOOT_BUDGET_MS}} ms +- {{BOOT_TOLERANCE_MS}} ms",
        ),
    ]
    assert all(r["collapsed"] is False and r["id"] for r in tc.steps)
    assert [p.name for p in doc.parameters] == [
        "BOOT_CYCLES",
        "BOOT_BUDGET_MS",
        "BOOT_TOLERANCE_MS",
    ]


def test_step_lines_outside_a_test_case_stay_text():
    doc = parse_markdown_document("## [REQ] Boot\n- Step: not a test case row\n")
    assert doc.sections[0].steps == []
    assert doc.sections[0].body == "- Step: not a test case row"
