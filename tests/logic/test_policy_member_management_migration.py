"""The migration that removes project member management from stored policies."""

import importlib.util
from pathlib import Path

_PATH = next(
    (Path(__file__).resolve().parents[2] / "alembic" / "versions").glob("449b8eddaf9e_*.py")
)
_SPEC = importlib.util.spec_from_file_location("policies_without_member_management", _PATH)
migration = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(migration)


def test_member_resource_and_manage_action_are_removed():
    stored = {
        "REQ": ["view", "review"],
        "member": ["view", "manage"],
        "TS": ["plan", "manage"],
        "*": ["*"],
    }
    assert migration.without_member_management(stored) == {
        "REQ": ["view", "review"],
        "TS": ["plan"],
        "*": ["*"],
    }


def test_a_matrix_without_member_management_is_unchanged():
    matrix = {"REQ": ["view"], "baseline": ["approve"]}
    assert migration.without_member_management(matrix) == matrix


def test_downgrade_gives_member_view_and_manage_back():
    assert migration.with_member_management({"REQ": ["view"]}) == {
        "REQ": ["view"],
        "member": ["manage", "view"],
    }
