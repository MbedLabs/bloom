import importlib.util
from pathlib import Path

from app.core.database import Base


def _load_revision_module(filename: str, module_name: str):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_baseline_creates_base_schema(monkeypatch):
    revision = _load_revision_module(
        "ebbcbf973496_add_project_memberships.py",
        "bloom_alembic_ebbcbf973496_add_project_memberships",
    )
    bind = object()
    calls: list[object] = []
    monkeypatch.setattr(revision.op, "get_bind", lambda: bind)
    monkeypatch.setattr(
        Base.metadata,
        "create_all",
        lambda *, bind: calls.append(bind),
    )

    revision.upgrade()

    assert calls == [bind]
