"""The one text form of test-case step rows, shared by every import and export.

A row is written ``- Pre-Condition: text``, ``- Step: action => expected`` or
``- Loop: text``, indented by two spaces per nesting level. It maps onto the steps table
of the editor: ``row_type``, ``label``, ``description``, ``expected_result``,
``indent_level``, ``collapsed`` and ``id``. A line that is not a row continues the row
above it, so multi-line text survives a CSV or XML cell. Text without any row line is
read in the older numbered form ``1. action => expected``, one step per line, so files
exported before the row form still import.
"""

import re
from typing import Iterable, Optional

STEP_ROW_RE = re.compile(
    r"^(?P<indent>[ \t]*)[-*]\s+(?P<label>pre-?condition|step|loop)\s*:(?P<text>.*)$",
    re.IGNORECASE,
)
_NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s(?P<text>.*)$")
_ROW_TYPES = {
    "pre-condition": "precondition",
    "precondition": "precondition",
    "step": "step",
    "loop": "loop",
}
LABELS = {"precondition": "Pre-Condition", "step": "Step", "loop": "Loop"}
EXPECTED_SEPARATOR = " => "


def make_row(
    row_type: str, description: str, expected: str = "", indent: int = 0, index: int = 0
) -> dict:
    """A step row in the editor's contract."""
    return {
        "id": f"row-{index + 1}",
        "row_type": row_type,
        "label": LABELS[row_type],
        "description": description.strip(),
        "expected_result": expected.strip(),
        "indent_level": max(0, indent),
        "collapsed": False,
    }


def parse_row(line: str, index: int = 0) -> Optional[dict]:
    """Turn one ``- Step: action => expected`` line into a row, or None when it is not one."""
    match = STEP_ROW_RE.match(line)
    if not match:
        return None
    description, _, expected = match.group("text").lstrip().partition(EXPECTED_SEPARATOR)
    indent = match.group("indent").replace("\t", "  ")
    return make_row(
        _ROW_TYPES[match.group("label").lower()],
        description,
        expected,
        len(indent) // 2,
        index,
    )


def continue_row(row: dict, line: str) -> None:
    """Append a continuation line to the row's expected result, or its description."""
    text = line.strip()
    if row["expected_result"]:
        row["expected_result"] += "\n" + text
        return
    description, separator, expected = text.partition(EXPECTED_SEPARATOR)
    row["description"] = (row["description"] + "\n" + description.strip()).strip()
    if separator:
        row["expected_result"] = expected.strip()


def text_to_rows(text: Optional[str]) -> Optional[list]:
    """Read the text form back into rows; None when there is nothing to read."""
    if not text or not text.strip():
        return None
    lines = [line for line in text.splitlines() if line.strip()]
    rows: list = []
    if any(STEP_ROW_RE.match(line) for line in lines):
        for line in lines:
            row = parse_row(line, len(rows))
            if row is not None:
                rows.append(row)
            elif rows:
                continue_row(rows[-1], line)
            else:
                rows.append(make_row("step", line, index=0))
        return rows
    for line in lines:
        match = _NUMBERED_RE.match(line)
        body = match.group("text").lstrip() if match else line.strip()
        description, _, expected = body.partition(EXPECTED_SEPARATOR)
        rows.append(make_row("step", description, expected, index=len(rows)))
    return rows


def _row_fields(step) -> dict:
    """Read a stored step, in the row contract or an older shape, as row fields."""
    if not isinstance(step, dict):
        return make_row("step", str(step))
    row_type = step.get("row_type") if step.get("row_type") in LABELS else "step"
    description = step.get("description")
    if description is None:
        description = step.get("action") or step.get("step") or ""
    expected = step.get("expected_result")
    if expected is None:
        expected = step.get("expected") or ""
    indent = step.get("indent_level") if isinstance(step.get("indent_level"), int) else 0
    return make_row(row_type, str(description), str(expected), indent)


def _row_lines(row: dict) -> list:
    """The lines one row is written as, continuation lines indented under it."""
    pad = "  " * row["indent_level"]
    description_lines = row["description"].splitlines() or [""]
    expected_lines = row["expected_result"].splitlines()
    lines = [f"{pad}- {row['label']}: {description_lines[0]}".rstrip()]
    lines.extend(f"{pad}  {extra}" for extra in description_lines[1:])
    if expected_lines:
        lines[-1] = f"{lines[-1]}{EXPECTED_SEPARATOR}{expected_lines[0]}"
        lines.extend(f"{pad}  {extra}" for extra in expected_lines[1:])
    return lines


def rows_to_text(steps) -> str:
    """Write stored steps in the text form."""
    if not steps:
        return ""
    if isinstance(steps, dict):
        inner = steps.get("steps")
        if not isinstance(inner, list):
            return "\n".join(f"{key}: {value}" for key, value in steps.items())
        steps = inner
    if not isinstance(steps, list):
        return str(steps)
    lines: list = []
    for step in steps:
        lines.extend(_row_lines(_row_fields(step)))
    return "\n".join(lines)


def has_precondition_rows(steps: Iterable) -> bool:
    """Whether stored steps already carry precondition rows."""
    return any(isinstance(s, dict) and s.get("row_type") == "precondition" for s in steps or [])


ROW_TYPE_VALUES = ("precondition", "pre-condition", "step", "loop")


class StepRowError(ValueError):
    """A step row whose ``row_type`` is none of the accepted values."""

    def __init__(self, position: int, value) -> None:
        self.position = position
        self.value = value
        super().__init__(
            f"Step row {position}: row_type {value!r} is not one of "
            + ", ".join(ROW_TYPE_VALUES)
            + " (in any letter case)."
        )


def row_type_of(value) -> Optional[str]:
    """The row type a ``row_type`` or ``label`` value names in any letter case, or None."""
    if not isinstance(value, str):
        return None
    return _ROW_TYPES.get(value.strip().lower())


def _first_text(step: dict, keys: tuple) -> str:
    """The first of the keys holding non-empty text, else an empty string."""
    for key in keys:
        value = step.get(key)
        if value is not None and str(value) != "":
            return str(value)
    return ""


def _indent(value) -> int:
    """An indent level of 0 or more; 0 for anything that is not a whole number."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float) and value.is_integer():
        return max(0, int(value))
    return 0


def _normal_row(step, position: int, strict: bool) -> dict:
    """One stored row in the editor's form, with its other keys kept.

    A ``row_type`` is read in any letter case; a row without one takes it from its
    ``label``, else is a step. Another ``row_type`` raises ``StepRowError`` when
    ``strict``, else the row is a step."""
    if not isinstance(step, dict):
        return {**make_row("step", str(step), index=position - 1), "id": None}
    raw_type = step.get("row_type")
    if raw_type is None or (isinstance(raw_type, str) and not raw_type.strip()):
        row_type = row_type_of(step.get("label")) or "step"
    else:
        row_type = row_type_of(raw_type)
        if row_type is None:
            if strict:
                raise StepRowError(position, raw_type)
            row_type = "step"
    label = step.get("label")
    row_id = step.get("id")
    return {
        **step,
        "id": row_id if isinstance(row_id, str) and row_id.strip() else None,
        "row_type": row_type,
        "label": label if isinstance(label, str) and label.strip() else LABELS[row_type],
        "description": _first_text(step, ("description", "action", "step")),
        "expected_result": _first_text(step, ("expected_result", "expected")),
        "indent_level": _indent(step.get("indent_level")),
        "collapsed": bool(step.get("collapsed")),
    }


def _give_ids(rows: list) -> None:
    """Give each row without an id ``row-N`` by its position, unique within the rows."""
    taken = {row["id"] for row in rows if row["id"]}
    for position, row in enumerate(rows, start=1):
        if row["id"]:
            continue
        candidate = f"row-{position}"
        suffix = 1
        while candidate in taken:
            suffix += 1
            candidate = f"row-{position}-{suffix}"
        row["id"] = candidate
        taken.add(candidate)


def normalize_rows(steps, preconditions: Optional[str] = None, strict: bool = True):
    """Stored test case rows in the editor's form, with the precondition text folded in.

    Each row gets ``id``, ``row_type``, ``label``, ``description``, ``expected_result``,
    ``indent_level`` and ``collapsed``: the description from ``description``, else
    ``action``, else ``step``, and the expected result from ``expected_result``, else
    ``expected``. Each non-empty line of ``preconditions`` becomes a precondition row
    before the other rows, unless a precondition row with that description exists.
    With ``strict`` an unknown ``row_type`` raises ``StepRowError``. A ``{"steps": [...]}``
    object is read as its list. None when there are no steps and no precondition lines."""
    if isinstance(steps, dict) and isinstance(steps.get("steps"), list):
        steps = steps["steps"]
    rows = [_normal_row(step, index, strict) for index, step in enumerate(steps or [], start=1)]
    held = {row["description"].strip() for row in rows if row["row_type"] == "precondition"}
    added = []
    for line in (preconditions or "").splitlines():
        text = line.strip()
        if text and text not in held:
            held.add(text)
            added.append({**make_row("precondition", text), "id": None})
    rows = added + rows
    if steps is None and not rows:
        return None
    _give_ids(rows)
    return rows
