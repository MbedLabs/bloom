"""The migration chain must stay a single explicit-DDL baseline.

The schema used to be built by a base revision that called
``Base.metadata.create_all()``. That made the baseline mirror whatever the models
currently described, so every later revision found its columns already present on
a fresh install and had to be written with inspect-then-add guards - and the real
ALTER path was therefore never exercised by the empty-database CI check.

The retired chain also carried data-only revisions (membership backfill,
relationship-type canonicalisation, disabling integrations left without
credentials). Those were one-time fixes: they match no rows on an empty database
and every deployed database has already applied them, so the tests that covered
them retired with the revisions themselves.

These tests pin the replacement contract.
"""

import ast
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"

# Deliberately equal to the head the previously deployed chain ended on, so a
# database already at that revision is seen as up to date and never re-migrated.
EXPECTED_HEAD = "d20260731a09"
BASELINE_FILE = f"{EXPECTED_HEAD}_locked_baseline_schema.py"


def _baseline_source() -> str:
    return (VERSIONS_DIR / BASELINE_FILE).read_text()


def _revision_files() -> list[Path]:
    return sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")


def test_the_baseline_is_still_the_only_root():
    """Revisions may follow the baseline; none may sit beside it.

    The rule this file exists to pin is that the schema is not rebuilt from the
    models - not that the schema can never change again. What must stay true is
    that every revision descends from the baseline, so a fresh database and a
    deployed one walk the same path and the ALTER steps are really exercised.
    """
    roots = [
        path.name
        for path in _revision_files()
        if "down_revision: Union[str, Sequence[str], None] = None" in path.read_text()
        or "down_revision = None" in path.read_text()
    ]

    assert roots == [BASELINE_FILE]


def test_every_later_revision_names_a_parent():
    for path in _revision_files():
        if path.name == BASELINE_FILE:
            continue
        source = path.read_text()
        # A revision with no parent is a second root: alembic would refuse to
        # pick a head, and one of the two branches would never run.
        assert "down_revision = " in source, path.name
        assert "down_revision = None" not in source, path.name


def test_no_later_revision_rebuilds_the_schema_from_the_models():
    """The guard that made the squash worth doing, applied to what comes after."""
    for path in _revision_files():
        if path.name == BASELINE_FILE:
            continue
        assert "create_all" not in path.read_text(), path.name


def test_baseline_is_the_root_and_keeps_the_deployed_head_id():
    source = _baseline_source()

    assert f'revision: str = "{EXPECTED_HEAD}"' in source
    assert "down_revision: Union[str, Sequence[str], None] = None" in source


def _create_all_calls() -> list[str]:
    """Names of any create_all calls in the baseline.

    Checked through the AST rather than by text search, because the module
    docstring mentions create_all while explaining why it is gone.
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(_baseline_source())):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "create_all":
            found.append(func.attr)
        elif isinstance(func, ast.Name) and func.id == "create_all":
            found.append(func.id)
    return found


def test_baseline_uses_explicit_ddl_not_create_all():
    """A models-derived baseline is what forced every later migration to be guarded."""
    assert _create_all_calls() == []
    assert "op.create_table(" in _baseline_source()


@pytest.mark.parametrize(
    "table", ["users", "projects", "requirements", "defects", "change_requests"]
)
def test_baseline_creates_the_core_tables(table):
    assert f'"{table}"' in _baseline_source()


def test_baseline_keeps_indexes_that_the_models_do_not_declare():
    """Autogenerate only sees the models, so these were nearly lost in the squash."""
    source = _baseline_source()

    assert "ix_defects_project_id" in source
    assert "ix_artefact_links_project_types" in source
    assert "pg_trgm" in source
    assert "gin_trgm_ops" in source


def test_baseline_drops_enum_types_on_downgrade():
    """Alembic drops tables but not their enum types, which breaks a re-upgrade."""
    assert "DROP TYPE IF EXISTS" in _baseline_source()
