"""The migration that keys stored policy permission matrices by document type."""

import importlib.util
from pathlib import Path

_PATH = next(
    (Path(__file__).resolve().parents[2] / "alembic" / "versions").glob("fda71a60c062_*.py")
)
_SPEC = importlib.util.spec_from_file_location("policy_permission_keys", _PATH)
migration = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(migration)


def test_resource_names_become_document_types():
    legacy = {
        "requirement": ["view", "edit"],
        "test_case": ["view"],
        "document": ["view", "import"],
        "run": ["execute"],
        "member": ["manage"],
        "parameter": ["view"],
        "*": ["*"],
    }
    assert migration.to_document_types(legacy) == {
        "REQ": ["edit", "view"],
        "TC": ["view"],
        "SPEC": ["import", "view"],
        "PRT": ["import", "view"],
        "RPT": ["import", "view"],
        "STD": ["import", "view"],
        "member": ["manage"],
        "parameter": ["view"],
        "*": ["*"],
    }


def test_downgrade_restores_the_resource_names():
    keyed = {"DES": ["view"], "SPEC": ["view"], "STD": ["edit"], "link": ["create"]}
    assert migration.to_resource_names(keyed) == {
        "design": ["view"],
        "document": ["edit", "view"],
        "link": ["create"],
    }


def test_a_matrix_already_keyed_by_document_type_is_unchanged():
    keyed = {"REQ": ["view"], "SPEC": ["edit"], "baseline": ["create"]}
    assert migration.to_document_types(keyed) == keyed
