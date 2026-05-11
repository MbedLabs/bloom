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


def test_requirement_create_has_no_client_req_id():
    r = RequirementCreate(project_id=1, title="Title")
    assert r.project_id == 1
    assert r.title == "Title"
    assert "req_id" not in RequirementCreate.model_fields


def test_testcase_create_has_no_client_tc_id():
    t = TestCaseCreate(project_id=1, title="TC Title")
    assert t.project_id == 1
    assert "tc_id" not in TestCaseCreate.model_fields


def test_document_create_has_no_client_doc_id():
    d = DocumentCreate(project_id=1, title="Spec", doc_type="SPEC")
    assert d.doc_type == "SPEC"
    assert "doc_id" not in DocumentCreate.model_fields


def test_design_risk_change_concept_create_without_public_ids():
    assert "design_id" not in DesignItemCreate.model_fields
    assert "risk_id" not in RiskItemCreate.model_fields
    assert "change_id" not in ChangeRequestCreate.model_fields
    assert "concept_id" not in TestConceptCreate.model_fields

    DesignItemCreate(project_id=1, title="D")
    RiskItemCreate(project_id=1, title="R")
    ChangeRequestCreate(project_id=1, title="C")
    TestConceptCreate(project_id=1, name="N")
