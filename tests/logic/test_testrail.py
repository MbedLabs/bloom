"""TestRail readers: XML suites and CSV exports into one case model."""

import pytest

from app.core import testrail
from app.core.config import settings
from app.core.testrail import (
    TestRailParseError,
    detect_columns,
    normalize_case_id,
    parse_testrail_csv,
    parse_testrail_xml,
    read_csv_header,
)

SUITE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<suite>
  <id>S1</id><name>Firmware</name>
  <sections>
    <section>
      <name>Boot</name>
      <cases>
        <case>
          <id>C7</id><title>Cold boot</title><template>Test Case (Steps)</template>
          <type>Functional</type><priority>High</priority><estimate>5m</estimate>
          <references>ALP-REQ-001, JIRA-9</references>
          <custom>
            <preconds>Relay open

Serial console attached</preconds>
            <steps_separated>
              <step><index>1</index><content>Close the relay</content><expected>Relay closed</expected></step>
              <step><index>2</index><content>Read the serial port</content><expected>Boot banner</expected></step>
            </steps_separated>
          </custom>
        </case>
      </cases>
      <sections>
        <section>
          <name>Warm</name>
          <cases>
            <case>
              <id>8</id><title>Warm boot</title><template>Test Case (Text)</template>
              <custom><steps>Reset the board</steps><expected>Banner within budget</expected></custom>
            </case>
          </cases>
        </section>
      </sections>
    </section>
  </sections>
</suite>"""


def _rows(case):
    return [(r["row_type"], r["description"], r["expected_result"]) for r in case.rows]


def test_xml_separated_steps_and_preconditions():
    cold, warm = parse_testrail_xml(SUITE_XML)
    assert (cold.case_id, cold.title, cold.sections) == ("C7", "Cold boot", ["Boot"])
    assert (cold.case_type, cold.priority, cold.estimate) == ("Functional", "High", "5m")
    assert cold.references == ["ALP-REQ-001", "JIRA-9"]
    assert _rows(cold) == [
        ("precondition", "Relay open", ""),
        ("precondition", "Serial console attached", ""),
        ("step", "Close the relay", "Relay closed"),
        ("step", "Read the serial port", "Boot banner"),
    ]
    assert [r["id"] for r in cold.rows] == ["row-1", "row-2", "row-3", "row-4"]


def test_xml_text_template_and_nested_section_path():
    warm = parse_testrail_xml(SUITE_XML)[1]
    assert warm.case_id == "C8"
    assert warm.sections == ["Boot", "Warm"]
    assert _rows(warm) == [("step", "Reset the board", "Banner within budget")]


def test_xml_rejects_what_it_cannot_read():
    with pytest.raises(TestRailParseError, match="not valid XML"):
        parse_testrail_xml(b"<suite><sections>")
    with pytest.raises(TestRailParseError, match="no <suite>"):
        parse_testrail_xml(b"<cases/>")


def test_xml_limits(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_OBJECTS", 1)
    with pytest.raises(TestRailParseError, match="more than 1 test cases"):
        parse_testrail_xml(SUITE_XML)
    monkeypatch.setattr(settings, "REQIF_MAX_OBJECTS", 999)
    monkeypatch.setattr(settings, "REQIF_MAX_HIERARCHY_DEPTH", 1)
    with pytest.raises(TestRailParseError, match="nested deeper"):
        parse_testrail_xml(SUITE_XML)
    monkeypatch.setattr(settings, "REQIF_MAX_REQUEST_BYTES", 10)
    with pytest.raises(TestRailParseError, match="size limit"):
        parse_testrail_xml(SUITE_XML)


def test_case_id_normalisation():
    assert [normalize_case_id(v) for v in ("123", "C123", "c123", "", "X-1")] == [
        "C123",
        "C123",
        "C123",
        "",
        "X-1",
    ]


SEPARATED_CSV = (
    "﻿ID,Title,Section Hierarchy,Type,Priority,Estimate,References,Preconditions,"
    "Steps (Step),Steps (Expected Result)\n"
    'C7,Cold boot,Firmware > Boot,Functional,High,5m,"ALP-REQ-001, JIRA-9",Relay open,'
    "Close the relay,Relay closed\n"
    "C7,,,,,,,,Read the serial port,Boot banner\n"
    'C9,Soak,Firmware > Soak,,,,,,"1. Start the soak\n2. Wait\nstill waiting","1. Running\n2. Done"\n'
).encode("utf-8")


def test_csv_one_row_per_step_groups_by_id():
    cold, soak = parse_testrail_csv(SEPARATED_CSV)
    assert (cold.case_id, cold.title, cold.sections) == ("C7", "Cold boot", ["Firmware", "Boot"])
    assert cold.references == ["ALP-REQ-001", "JIRA-9"]
    assert _rows(cold) == [
        ("precondition", "Relay open", ""),
        ("step", "Close the relay", "Relay closed"),
        ("step", "Read the serial port", "Boot banner"),
    ]
    assert _rows(soak) == [
        ("step", "Start the soak", "Running"),
        ("step", "Wait\nstill waiting", "Done"),
    ]


def test_csv_text_template():
    data = b"Title,Steps,Expected Result\nWarm boot,Reset the board,Banner\n"
    (case,) = parse_testrail_csv(data)
    assert _rows(case) == [("step", "Reset the board", "Banner")]
    assert case.case_id == "" and case.sections == []


def test_csv_column_mapping_and_errors():
    data = b"Name,Do,Expect\nCold boot,Close relay,Closed\n"
    with pytest.raises(TestRailParseError, match="no Title column"):
        parse_testrail_csv(data)
    (case,) = parse_testrail_csv(data, {"title": "Name", "steps": "Do", "expected": "Expect"})
    assert (case.title, _rows(case)) == ("Cold boot", [("step", "Close relay", "Closed")])
    with pytest.raises(TestRailParseError, match="no column named 'Nope'"):
        parse_testrail_csv(data, {"title": "Nope"})
    with pytest.raises(TestRailParseError, match="no Title column"):
        parse_testrail_csv(b"Title\nx\n", {"title": ""})
    with pytest.raises(TestRailParseError, match="Unknown field"):
        parse_testrail_csv(data, {"colour": "Name"})
    with pytest.raises(TestRailParseError, match="not UTF-8"):
        parse_testrail_csv(b"\xff\xfeT\x00")
    with pytest.raises(TestRailParseError, match="empty"):
        parse_testrail_csv(b"")


def test_detected_columns_and_header():
    header = read_csv_header(SEPARATED_CSV)
    assert header[0] == "ID"
    detected = detect_columns(header)
    assert detected["title"] == "Title"
    assert detected["step"] == "Steps (Step)"
    assert detected["step_expected"] == "Steps (Expected Result)"
    assert "steps" not in detected


def test_csv_row_limit(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_RELATIONS", 1)
    with pytest.raises(TestRailParseError, match="more rows"):
        parse_testrail_csv(SEPARATED_CSV)


def test_module_exports_the_case_model():
    assert testrail.TestRailCase("C1", "t").rows == []
