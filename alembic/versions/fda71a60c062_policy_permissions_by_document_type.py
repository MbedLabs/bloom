"""policy permissions keyed by document type

Renames the resource keys of every stored policy permission matrix to the document
type codes: requirement REQ, test_case TC, design DES, risk RSK, change_request CHG,
test_concept CPT, defect DEF, campaign CMP, suite TS. The document key becomes SPEC,
PRT, RPT and STD with the same actions. The run key is removed. baseline, parameter,
link, member and the wildcard are unchanged. Downgrade renames the keys back and joins
SPEC, PRT, RPT and STD into document.

Revision ID: fda71a60c062
Revises: e1a7c3f9b204
Create Date: 2026-09-27

"""

import sqlalchemy as sa

from alembic import op

revision = "fda71a60c062"
down_revision = "e1a7c3f9b204"
branch_labels = None
depends_on = None

RENAMED = {
    "requirement": "REQ",
    "test_case": "TC",
    "design": "DES",
    "risk": "RSK",
    "change_request": "CHG",
    "test_concept": "CPT",
    "defect": "DEF",
    "campaign": "CMP",
    "suite": "TS",
}
DOCUMENT_KINDS = ("SPEC", "PRT", "RPT", "STD")

policies = sa.table(
    "policies",
    sa.column("id", sa.Integer),
    sa.column("permissions", sa.JSON),
)


def _add(matrix: dict, key: str, actions) -> None:
    """Union the actions into the matrix entry for the key."""
    matrix[key] = sorted(set(matrix.get(key) or []) | set(actions or []))


def to_document_types(matrix: dict) -> dict:
    """The matrix with its resource keys renamed to document type codes."""
    result: dict = {}
    for key, actions in (matrix or {}).items():
        if key == "run":
            continue
        if key == "document":
            for kind in DOCUMENT_KINDS:
                _add(result, kind, actions)
        else:
            _add(result, RENAMED.get(key, key), actions)
    return result


def to_resource_names(matrix: dict) -> dict:
    """The matrix with document type codes renamed back to the resource names."""
    back = {code: name for name, code in RENAMED.items()}
    result: dict = {}
    for key, actions in (matrix or {}).items():
        if key in DOCUMENT_KINDS:
            _add(result, "document", actions)
        else:
            _add(result, back.get(key, key), actions)
    return result


def _rewrite(convert) -> None:
    """Apply the conversion to every stored policy matrix that it changes."""
    bind = op.get_bind()
    rows = bind.execute(sa.select(policies.c.id, policies.c.permissions)).all()
    for row in rows:
        converted = convert(row.permissions or {})
        if converted != (row.permissions or {}):
            bind.execute(
                policies.update().where(policies.c.id == row.id).values(permissions=converted)
            )


def upgrade() -> None:
    _rewrite(to_document_types)


def downgrade() -> None:
    _rewrite(to_resource_names)
