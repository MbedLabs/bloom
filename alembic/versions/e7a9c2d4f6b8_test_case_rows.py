"""test case rows

Revision ID: e7a9c2d4f6b8
Revises: d4e6f8a1c3b5
Create Date: 2026-11-18

Stores every test case's steps in the editor's form: a ``row_type`` is read in any letter case
(``Pre-Condition`` and ``pre-condition`` are a precondition), a row without one takes it from its
``label``, else is a step, and a stored unknown ``row_type`` becomes a step with a log line naming
the test case. ``description`` comes from ``description``, ``action`` or ``step``,
``expected_result`` from ``expected_result`` or ``expected``, and each row carries ``id``,
``row_type``, ``label``, ``description``, ``expected_result``, ``indent_level`` and ``collapsed``.
Each non-empty line of ``preconditions`` becomes a precondition row before the other rows, unless a
precondition row with that description exists, and ``preconditions`` is then null. A test case in
that form is left as it is. Downgrade keeps the rows.
"""

import logging

import sqlalchemy as sa

from alembic import op

revision = "e7a9c2d4f6b8"
down_revision = "d4e6f8a1c3b5"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

ROW_TYPES = {
    "pre-condition": "precondition",
    "precondition": "precondition",
    "step": "step",
    "loop": "loop",
}
LABELS = {"precondition": "Pre-Condition", "step": "Step", "loop": "Loop"}

test_cases = sa.table(
    "test_cases",
    sa.column("id", sa.Integer),
    sa.column("tc_id", sa.String),
    sa.column("steps", sa.JSON),
    sa.column("preconditions", sa.Text),
)


def _row_type(value):
    """The row type a value names in any letter case, or None."""
    return ROW_TYPES.get(value.strip().lower()) if isinstance(value, str) else None


def _text(step: dict, keys: tuple) -> str:
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


def _row(step, position: int, tc_id: str) -> dict:
    """One row in the editor's form, with its other keys kept."""
    if not isinstance(step, dict):
        step = {"description": str(step)}
    raw = step.get("row_type")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        row_type = _row_type(step.get("label")) or "step"
    else:
        row_type = _row_type(raw)
        if row_type is None:
            logger.info(
                "test case %s: row %s has row_type %r, stored as a step", tc_id, position, raw
            )
            row_type = "step"
    label = step.get("label")
    row_id = step.get("id")
    return {
        **step,
        "id": row_id if isinstance(row_id, str) and row_id.strip() else None,
        "row_type": row_type,
        "label": label if isinstance(label, str) and label.strip() else LABELS[row_type],
        "description": _text(step, ("description", "action", "step")),
        "expected_result": _text(step, ("expected_result", "expected")),
        "indent_level": _indent(step.get("indent_level")),
        "collapsed": bool(step.get("collapsed")),
    }


def _rows(steps, preconditions, tc_id: str):
    """The test case's rows in the editor's form with its precondition lines folded in, or None."""
    if isinstance(steps, dict) and isinstance(steps.get("steps"), list):
        steps = steps["steps"]
    if not isinstance(steps, list):
        steps = [] if steps is None else [steps]
    rows = [_row(step, position, tc_id) for position, step in enumerate(steps, start=1)]
    held = {row["description"].strip() for row in rows if row["row_type"] == "precondition"}
    added = []
    for line in (preconditions or "").splitlines():
        text = line.strip()
        if text and text not in held:
            held.add(text)
            added.append(
                {
                    "id": None,
                    "row_type": "precondition",
                    "label": LABELS["precondition"],
                    "description": text,
                    "expected_result": "",
                    "indent_level": 0,
                    "collapsed": False,
                }
            )
    rows = added + rows
    if not rows:
        return None
    taken = {row["id"] for row in rows if row["id"]}
    for position, row in enumerate(rows, start=1):
        if row["id"]:
            continue
        candidate, suffix = f"row-{position}", 1
        while candidate in taken:
            suffix += 1
            candidate = f"row-{position}-{suffix}"
        row["id"] = candidate
        taken.add(candidate)
    return rows


def upgrade() -> None:
    """Store every test case's steps in the editor's form with its precondition lines folded in."""
    bind = op.get_bind()
    for case_id, tc_id, steps, preconditions in bind.execute(
        sa.select(
            test_cases.c.id, test_cases.c.tc_id, test_cases.c.steps, test_cases.c.preconditions
        )
    ).all():
        rows = _rows(steps, preconditions, tc_id)
        if rows == steps and preconditions is None:
            continue
        bind.execute(
            test_cases.update()
            .where(test_cases.c.id == case_id)
            .values(steps=rows if rows is not None else steps, preconditions=None)
        )


def downgrade() -> None:
    """Keep the stored rows."""
