"""
Project naming validation.
"""

import pytest
from pydantic import ValidationError

from app.schemas import (
    ChangeRequestCreate,
    DesignItemCreate,
    DocumentCreate,
    ProjectCreate,
    ProjectUpdate,
    RequirementCreate,
    RiskItemCreate,
    TestCaseCreate,
    TestConceptCreate,
)


def test_project_prefix_is_normalized_for_id_convention():
    project = ProjectCreate(name="Controller", prefix=" vcu ")

    assert project.prefix == "VCU"


@pytest.mark.parametrize(
    "prefix", ["BLOOM", "VC1", "VCU-1", "VCU REQ", "1VCU", "VCU_REQ", "VCU.REQ"]
)
def test_project_prefix_rejects_values_that_break_generated_ids(prefix):
    with pytest.raises(ValidationError):
        ProjectCreate(name="Controller", prefix=prefix)


def test_project_update_rejects_invalid_prefix():
    with pytest.raises(ValidationError):
        ProjectUpdate(prefix="PRJ-REQ-001")


@pytest.mark.parametrize(
    ("schema", "field", "doc_id"),
    [
        (RequirementCreate, "req_id", "PRJ-REQ-001"),
        (TestCaseCreate, "tc_id", "PRJ-TC-001"),
        (DocumentCreate, "doc_id", "PRJ-SPEC-001"),
        (DesignItemCreate, "design_id", "PRJ-DES-001"),
        (RiskItemCreate, "risk_id", "PRJ-RSK-001"),
        (ChangeRequestCreate, "change_id", "PRJ-CHG-001"),
        (TestConceptCreate, "concept_id", "PRJ-TCO-001"),
    ],
)
def test_creator_supplied_ids_are_required_and_normalized(schema, field, doc_id):
    title_field = "name" if schema is TestConceptCreate else "title"
    item = schema(project_id=1, **{field: doc_id.lower(), title_field: "Title"})

    assert getattr(item, field) == doc_id


@pytest.mark.parametrize("doc_id", ["PR1-REQ-001", "PRJ-BUG-001", "PRJ-REQ-1", "PRJ-REQ-1000"])
def test_creator_supplied_requirement_id_must_match_convention(doc_id):
    with pytest.raises(ValidationError):
        RequirementCreate(project_id=1, req_id=doc_id, title="Title")


def test_shared_document_id_type_must_match_document_type():
    with pytest.raises(ValidationError):
        DocumentCreate(project_id=1, doc_id="PRJ-RPT-001", doc_type="SPEC", title="Title")
