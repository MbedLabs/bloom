"""Read TestRail exports, XML and CSV, into one case model for migration into Bloom.

Both readers produce ``TestRailCase`` objects: the TestRail id, title, section path,
preconditions, step rows in the editor contract, type, priority, estimate and the
references. The XML is one ``<suite>`` of nested ``<sections>``; a case keeps its steps
either as ``steps_separated`` ``<step>`` elements or as one ``steps``/``expected`` pair.
The CSV carries whatever columns the user ticked, matched by header name with the
TestRail defaults known and an optional mapping, and may repeat a case on one row per
step. Limits come from the ReqIF settings so a hostile file cannot hold the process.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Optional

from defusedxml import ElementTree as SafeET

from app.core.config import settings
from app.core.tc_steps import make_row


class TestRailParseError(ValueError):
    """The file is not a TestRail export Bloom can read."""

    __test__ = False


@dataclass
class TestRailCase:
    """One TestRail case, independent of the export format it came from."""

    __test__ = False

    case_id: str
    title: str
    sections: list = field(default_factory=list)
    preconditions: str = ""
    rows: list = field(default_factory=list)
    case_type: str = ""
    priority: str = ""
    estimate: str = ""
    references: list = field(default_factory=list)


CSV_FIELDS = {
    "id": ("id",),
    "title": ("title",),
    "section": ("section",),
    "section_hierarchy": ("section hierarchy",),
    "type": ("type",),
    "priority": ("priority",),
    "estimate": ("estimate",),
    "references": ("references",),
    "preconditions": ("preconditions",),
    "steps": ("steps",),
    "expected": ("expected result",),
    "step": ("steps (step)",),
    "step_expected": ("steps (expected result)",),
}
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+")


def normalize_case_id(raw: Optional[str]) -> str:
    """``123`` and ``C123`` both become ``C123``; empty stays empty."""
    raw = (raw or "").strip()
    if raw[:1] in ("C", "c") and raw[1:].isdigit():
        return "C" + raw[1:]
    if raw.isdigit():
        return "C" + raw
    return raw


def split_references(raw: Optional[str]) -> list:
    """The reference tokens, usually issue or requirement keys separated by commas."""
    return [token for token in re.split(r"[,;\s]+", raw or "") if token]


def _precondition_rows(text: str) -> list:
    """One precondition row per paragraph."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return [make_row("precondition", p, index=i) for i, p in enumerate(paragraphs)]


def _renumber(rows: list) -> list:
    """Give the rows consecutive ids after they are assembled."""
    for index, row in enumerate(rows):
        row["id"] = f"row-{index + 1}"
    return rows


def _check_case_count(count: int) -> None:
    """Enforce the ReqIF object limit on the number of cases."""
    if count > settings.REQIF_MAX_OBJECTS:
        raise TestRailParseError(
            f"The file has more than {settings.REQIF_MAX_OBJECTS} test cases; split it by section."
        )


def _check_size(data: bytes) -> None:
    """Enforce the ReqIF request size limit."""
    if len(data) > settings.REQIF_MAX_REQUEST_BYTES:
        raise TestRailParseError("The file is larger than the import size limit.")


def _text(node, tag: str) -> str:
    """The stripped text of a child element, or an empty string."""
    child = node.find(tag) if node is not None else None
    return (child.text or "").strip() if child is not None and child.text else ""


def _xml_case(node, sections: list) -> TestRailCase:
    """Read one ``<case>`` element."""
    custom = node.find("custom")
    preconditions = _text(custom, "preconds")
    rows = _precondition_rows(preconditions)
    separated = custom.find("steps_separated") if custom is not None else None
    if separated is not None:
        for step in separated.findall("step"):
            rows.append(make_row("step", _text(step, "content"), _text(step, "expected")))
    elif custom is not None and (_text(custom, "steps") or _text(custom, "expected")):
        rows.append(make_row("step", _text(custom, "steps"), _text(custom, "expected")))
    return TestRailCase(
        case_id=normalize_case_id(_text(node, "id")),
        title=_text(node, "title"),
        sections=list(sections),
        preconditions=preconditions,
        rows=_renumber(rows),
        case_type=_text(node, "type"),
        priority=_text(node, "priority"),
        estimate=_text(node, "estimate"),
        references=split_references(_text(node, "references")),
    )


def _walk_sections(container, path: list, depth: int, cases: list) -> None:
    """Collect the cases of every ``<section>`` under ``container``, depth first."""
    if depth > settings.REQIF_MAX_HIERARCHY_DEPTH:
        raise TestRailParseError("The sections are nested deeper than the import limit.")
    sections = container.find("sections")
    if sections is None:
        return
    for section in sections.findall("section"):
        section_path = [*path, _text(section, "name")]
        case_list = section.find("cases")
        if case_list is not None:
            for node in case_list.findall("case"):
                cases.append(_xml_case(node, section_path))
                _check_case_count(len(cases))
        _walk_sections(section, section_path, depth + 1, cases)


def parse_testrail_xml(data: bytes) -> list:
    """Read a TestRail suite XML export into cases."""
    _check_size(data)
    try:
        root = SafeET.fromstring(data)
    except Exception as exc:
        raise TestRailParseError(f"The file is not valid XML: {exc}") from exc
    suite = root if root.tag == "suite" else root.find("suite")
    if suite is None:
        raise TestRailParseError("The file is not a TestRail suite export (no <suite>).")
    cases: list = []
    _walk_sections(suite, [], 1, cases)
    top_cases = suite.find("cases")
    if top_cases is not None:
        for node in top_cases.findall("case"):
            cases.append(_xml_case(node, []))
            _check_case_count(len(cases))
    return cases


def detect_columns(header: list) -> dict:
    """Map each known field to the header that carries it, by name, case-insensitively."""
    by_name = {name.strip().lower(): name for name in header}
    detected = {}
    for key, aliases in CSV_FIELDS.items():
        for alias in aliases:
            if alias in by_name:
                detected[key] = by_name[alias]
                break
    return detected


def _items(text: str) -> list:
    """Split a multi-step cell into steps: numbered lines start a step, else one per line."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not any(_NUMBERED.match(line) for line in lines):
        return [line.strip() for line in lines]
    items: list = []
    for line in lines:
        if _NUMBERED.match(line) or not items:
            items.append(_NUMBERED.sub("", line).strip())
        else:
            items[-1] = f"{items[-1]}\n{line.strip()}"
    return items


def _csv_step_rows(record: dict, columns: dict) -> list:
    """The step rows one CSV row carries, in either template."""
    step_cell = record.get(columns.get("step", ""), "") if "step" in columns else ""
    expected_cell = (
        record.get(columns.get("step_expected", ""), "") if "step_expected" in columns else ""
    )
    if step_cell.strip() or expected_cell.strip():
        steps = _items(step_cell)
        expected = _items(expected_cell)
        count = max(len(steps), len(expected))
        return [
            make_row(
                "step",
                steps[i] if i < len(steps) else "",
                expected[i] if i < len(expected) else "",
            )
            for i in range(count)
        ]
    text = record.get(columns["steps"], "") if "steps" in columns else ""
    expected_text = record.get(columns["expected"], "") if "expected" in columns else ""
    if text.strip() or expected_text.strip():
        return [make_row("step", text, expected_text)]
    return []


def _section_path(record: dict, columns: dict) -> list:
    """The section path, from Section Hierarchy (``A > B``) or Section."""
    hierarchy = (
        record.get(columns["section_hierarchy"], "") if "section_hierarchy" in columns else ""
    )
    if hierarchy.strip():
        return [part.strip() for part in hierarchy.split(">") if part.strip()]
    section = record.get(columns["section"], "") if "section" in columns else ""
    return [section.strip()] if section.strip() else []


def parse_testrail_csv(data: bytes, mapping: Optional[dict] = None) -> list:
    """Read a TestRail CSV export into cases, using the detected columns and ``mapping``."""
    _check_size(data)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TestRailParseError("The file is not UTF-8 text.") from exc
    csv.field_size_limit(settings.REQIF_MAX_REQUEST_BYTES)
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        raise TestRailParseError("The file is empty.")
    columns = detect_columns(header)
    for key, name in (mapping or {}).items():
        if key not in CSV_FIELDS:
            raise TestRailParseError(f"Unknown field in the column mapping: {key}.")
        if name and name not in header:
            raise TestRailParseError(f"The file has no column named {name!r}.")
        if name:
            columns[key] = name
        else:
            columns.pop(key, None)
    if "title" not in columns:
        raise TestRailParseError("The file has no Title column.")
    cases: list = []
    current: Optional[TestRailCase] = None
    for count, values in enumerate(reader, start=1):
        if count > settings.REQIF_MAX_RELATIONS:
            raise TestRailParseError("The file has more rows than the import limit.")
        record = dict(zip(header, values))
        case_id = (
            normalize_case_id(record.get(columns.get("id", ""), "")) if "id" in columns else ""
        )
        title = record.get(columns["title"], "").strip()
        same_case = current is not None and case_id and case_id == current.case_id
        if same_case and (not title or title == current.title):
            current.rows.extend(_csv_step_rows(record, columns))
            _renumber(current.rows)
            continue
        preconditions = (
            record.get(columns["preconditions"], "").strip() if "preconditions" in columns else ""
        )
        current = TestRailCase(
            case_id=case_id,
            title=title,
            sections=_section_path(record, columns),
            preconditions=preconditions,
            rows=_renumber(_precondition_rows(preconditions) + _csv_step_rows(record, columns)),
            case_type=record.get(columns["type"], "").strip() if "type" in columns else "",
            priority=record.get(columns["priority"], "").strip() if "priority" in columns else "",
            estimate=record.get(columns["estimate"], "").strip() if "estimate" in columns else "",
            references=(
                split_references(record.get(columns["references"], ""))
                if "references" in columns
                else []
            ),
        )
        cases.append(current)
        _check_case_count(len(cases))
    return cases


def read_csv_header(data: bytes) -> list:
    """The header row of a CSV upload, for the column-mapping step."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TestRailParseError("The file is not UTF-8 text.") from exc
    header = next(csv.reader(io.StringIO(text.split("\n", 1)[0])), None)
    if not header:
        raise TestRailParseError("The file is empty.")
    return header
