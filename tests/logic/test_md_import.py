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


def test_parameters_parsed():
    text = "## Parameters\nparameter: BOOT_MS\nvalue: 500\nparameter: MAX_TEMP\nvalue: 85C"
    doc = parse_markdown_document(text)
    assert [(p.name, p.value) for p in doc.parameters] == [
        ("BOOT_MS", "500"),
        ("MAX_TEMP", "85C"),
    ]


def test_parameter_collisions_require_action():
    params = [Parameter("BOOT_MS", "500"), Parameter("NEW_ONE", "1")]
    collisions = parameter_name_collisions(params, existing_names=["boot_ms", "other"])
    assert collisions == ["BOOT_MS"]
