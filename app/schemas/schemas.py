"""
Pydantic schemas for API request/response validation.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.core.id_generator import normalize_doc_id

# ==================== Project Schemas ====================

PROJECT_PREFIX_PATTERN = re.compile(r"^[A-Z]{3}$")
PROJECT_PREFIX_ERROR = (
    "Project prefix must be exactly three uppercase letters so generated IDs follow " "PRJ-TYP-001."
)


def normalize_project_prefix(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(PROJECT_PREFIX_ERROR)
    normalized = value.strip().upper()
    if not PROJECT_PREFIX_PATTERN.fullmatch(normalized):
        raise ValueError(PROJECT_PREFIX_ERROR)
    return normalized


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    prefix: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = None
    status: str = "Active"

    @field_validator("prefix", mode="before")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        return normalize_project_prefix(value)


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    prefix: Optional[str] = Field(None, min_length=1, max_length=10)
    description: Optional[str] = None
    status: Optional[str] = None

    @field_validator("prefix", mode="before")
    @classmethod
    def validate_prefix(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return normalize_project_prefix(value)


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: int
    name: str
    prefix: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    requirement_count: int = 0
    test_case_count: int = 0
    design_count: int = 0
    risk_count: int = 0
    change_count: int = 0
    test_concept_count: int = 0
    test_suite_count: int = 0
    defect_count: int = 0

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class ProjectVariableCreate(BaseModel):
    project_id: int
    kind: str = Field(default="variable", pattern="^(parameter|variable)$")
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)
    description: Optional[str] = None


class ProjectVariableUpdate(BaseModel):
    kind: Optional[str] = Field(default=None, pattern="^(parameter|variable)$")
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    value: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None


class ProjectVariableResponse(BaseModel):
    id: int
    project_id: int
    kind: str
    key: str
    value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class RequirementSummary(BaseModel):
    id: int
    req_id: str
    title: str
    status: str


class TestCaseSummary(BaseModel):
    id: int
    tc_id: str
    title: str
    status: str


class TestSuiteSummary(BaseModel):
    id: int
    suite_id: str
    name: str
    status: str


class TestCampaignSummary(BaseModel):
    id: int
    name: str
    status: str


class TestConceptSummary(BaseModel):
    id: int
    concept_id: str
    name: str
    status: str


class RequirementVerifiedByLinkResponse(BaseModel):
    id: int
    link_type: str
    created_at: datetime
    test_case: TestCaseSummary

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"


class TestCaseVerifiesLinkResponse(BaseModel):
    id: int
    link_type: str
    created_at: datetime
    requirement: RequirementSummary

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"


# ==================== Requirement Schemas ====================


class RequirementCreate(BaseModel):
    """Schema for creating a requirement."""

    project_id: int
    req_id: str = Field(..., min_length=11, max_length=12)
    parent_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Draft"
    priority: str = "Medium"
    req_type: str = "Functional"
    req_origin: str = "Internal"
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None

    @field_validator("req_id", mode="before")
    @classmethod
    def validate_req_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="REQ")


class RequirementUpdate(BaseModel):
    """Schema for updating a requirement."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    req_type: Optional[str] = None
    req_origin: Optional[str] = None
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    parent_id: Optional[int] = None


class RequirementResponse(BaseModel):
    """Schema for requirement response."""

    id: int
    project_id: int
    parent_id: Optional[int] = None
    req_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    req_type: str
    req_origin: str
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    children: List["RequirementResponse"] = []
    test_case_count: int = 0
    linked_test_cases: List[TestCaseSummary] = []
    verified_by: List[RequirementVerifiedByLinkResponse] = []
    linked_test_runs: List["TestRunLinkResponse"] = []
    suite_backlinks: List[TestSuiteSummary] = []
    campaign_backlinks: List[TestCampaignSummary] = []

    @field_serializer("created_at", "updated_at", "reviewed_at", "approved_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


# ==================== TestCase Schemas ====================


class TestCaseCreate(BaseModel):
    """Schema for creating a test case."""

    project_id: int
    tc_id: str = Field(..., min_length=10, max_length=10)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    status: str = "Draft"
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None

    @field_validator("tc_id", mode="before")
    @classmethod
    def validate_tc_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="TC")


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = None
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None


class TestCaseResponse(BaseModel):
    """Schema for test case response."""

    id: int
    project_id: int
    tc_id: str
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]]
    status: str
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    last_execution_status: Optional[str] = None
    last_executed_at: Optional[datetime] = None
    last_execution_comment: Optional[str] = None
    last_bud_run_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    requirement_count: int = 0
    linked_requirements: List[RequirementSummary] = []
    verifies: List[TestCaseVerifiesLinkResponse] = []
    suite_memberships: List[TestSuiteSummary] = []
    campaign_memberships: List[TestCampaignSummary] = []

    @field_serializer(
        "created_at",
        "updated_at",
        "reviewed_at",
        "approved_at",
        "last_executed_at",
    )
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


class RequirementLinkCreate(BaseModel):
    target_id: int
    link_type: str = "depends_on"


class RequirementLinkResponse(BaseModel):
    id: int
    source_id: int
    target_id: int
    link_type: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== TestRunLink Schemas ====================


class TestRunLinkCreate(BaseModel):
    """Schema for linking a test run to a requirement."""

    test_run_id: int
    test_run_name: Optional[str] = None
    teststation_url: Optional[str] = None
    status: Optional[str] = None


class TestRunLinkResponse(BaseModel):
    """Schema for test run link response."""

    id: int
    requirement_id: int
    test_run_id: int
    test_run_name: Optional[str] = None
    teststation_url: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Traceability Schemas ====================


class TraceabilityItem(BaseModel):
    requirement: RequirementResponse
    linked_test_cases: List[TestCaseResponse]
    linked_test_runs: List[TestRunLinkResponse]
    coverage_status: str


class ImpactNode(BaseModel):
    requirement: RequirementResponse
    link_type: str
    direction: str
    depth: int
    children: List["ImpactNode"] = []


class ImpactAnalysisResponse(BaseModel):
    root_requirement: RequirementResponse
    upstream: List[ImpactNode]
    downstream: List[ImpactNode]


class CoverageGap(BaseModel):
    requirement: RequirementResponse
    gap_type: str
    linked_test_cases: List[TestCaseResponse]
    all_test_cases_draft: bool
    missing_link_types: List[str]


class CoverageGapReport(BaseModel):
    project_id: int
    total_requirements: int
    covered: int
    partial: int
    uncovered: int
    coverage_percent: float
    gaps: List[CoverageGap]


# ==================== Health Schemas ====================


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str = "healthy"
    version: str
    database: str = "connected"


class VersionResponse(BaseModel):
    """Schema for version response."""

    version: str
    api_version: str = "v1"


class DocumentCreate(BaseModel):
    project_id: int
    doc_id: str = Field(..., min_length=11, max_length=12)
    title: str = Field(..., min_length=1, max_length=500)
    doc_type: str = Field(default="SPEC", pattern="^(SPEC|PROT|RPT|STD)$")
    description: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

    @field_validator("doc_id", mode="before")
    @classmethod
    def validate_doc_id(cls, value: str) -> str:
        return normalize_doc_id(value)

    @model_validator(mode="after")
    def validate_doc_id_type(self):
        self.doc_id = normalize_doc_id(self.doc_id, expected_type_code=self.doc_type)
        return self


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    doc_type: Optional[str] = Field(None, pattern="^(SPEC|PROT|RPT|STD)$")
    status: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class DocumentSectionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    section_type: str = "text"
    order: int = 0
    parent_section_id: Optional[int] = None


class DocumentSectionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    section_type: Optional[str] = None
    order: Optional[int] = None
    parent_section_id: Optional[int] = None


class DocumentSectionResponse(BaseModel):
    id: int
    document_id: int
    parent_section_id: Optional[int] = None
    order: int
    title: str
    content: Optional[str] = None
    section_type: str
    created_at: datetime
    updated_at: datetime
    child_sections: List["DocumentSectionResponse"] = []

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: int
    project_id: int
    doc_id: Optional[str] = None
    title: str
    doc_type: str
    status: str
    version: str
    description: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    section_count: int = 0

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    id: int
    project_id: int
    doc_id: Optional[str] = None
    title: str
    doc_type: str
    status: str
    version: str
    description: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sections: List[DocumentSectionResponse] = []

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class SectionReorder(BaseModel):
    section_orders: List[dict]


# ==================== Test Campaign Schemas ====================


class TestConfigurationCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    environment: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class TestConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    environment: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class TestConfigurationResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    environment: Optional[str] = None
    parameters: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class TestSuiteCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "Draft"
    test_case_ids: List[int] = []


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None


class TestSuiteItemResponse(BaseModel):
    id: int
    suite_id: int
    test_case_id: int
    order: int
    created_at: datetime
    test_case: Optional[TestCaseSummary] = None

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class TestSuiteResponse(BaseModel):
    id: int
    project_id: int
    suite_id: str
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    total_items: int = 0

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class TestSuiteDetailResponse(TestSuiteResponse):
    items: List[TestSuiteItemResponse] = []
    related_requirements: List[RequirementSummary] = []
    linked_campaigns: List[TestCampaignSummary] = []
    related_concepts: List[TestConceptSummary] = []


class TestCampaignCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    configuration_id: Optional[int] = None
    suite_id: Optional[int] = None
    suite_ids: List[int] = []
    bud_run_id: Optional[int] = None
    bud_run_url: Optional[str] = None
    bud_run_status: Optional[str] = None
    test_case_ids: List[int] = []


class TestCampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    configuration_id: Optional[int] = None
    suite_id: Optional[int] = None
    suite_ids: Optional[List[int]] = None
    bud_run_id: Optional[int] = None
    bud_run_url: Optional[str] = None
    bud_run_status: Optional[str] = None
    status: Optional[str] = None


class TestCampaignItemResponse(BaseModel):
    id: int
    campaign_id: int
    test_case_id: int
    status: str
    result: Optional[str] = None
    comment: Optional[str] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    test_case: Optional[TestCaseResponse] = None

    @field_serializer("executed_at", "created_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


class TestCampaignResponse(BaseModel):
    id: int
    project_id: int
    configuration_id: Optional[int] = None
    suite_id: Optional[int] = None
    bud_run_id: Optional[int] = None
    bud_run_url: Optional[str] = None
    bud_run_status: Optional[str] = None
    name: str
    description: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    total_items: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    pending: int = 0
    configuration: Optional[TestConfigurationResponse] = None
    suite: Optional[TestSuiteSummary] = None
    suites: List[TestSuiteSummary] = []

    @field_serializer("started_at", "completed_at", "created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


class TestCampaignSuiteScope(BaseModel):
    suite: TestSuiteSummary
    items: List[TestCampaignItemResponse] = []


class TestCampaignDetailResponse(TestCampaignResponse):
    items: List[TestCampaignItemResponse] = []
    suite_scopes: List[TestCampaignSuiteScope] = []
    ad_hoc_items: List[TestCampaignItemResponse] = []
    related_requirements: List[RequirementSummary] = []
    related_concepts: List[TestConceptSummary] = []


class TestCampaignItemUpdate(BaseModel):
    comment: Optional[str] = None


class ArtefactLinkCreate(BaseModel):
    project_id: int
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    role: str = Field(..., min_length=1, max_length=50)
    suspect: bool = False

    @field_validator("source_type", "target_type")
    @classmethod
    def normalize_type_fields(cls, value: str) -> str:
        return value.upper()

    @field_validator("role")
    @classmethod
    def normalize_role_field(cls, value: str) -> str:
        return value.lower()


class ArtefactLinkResponse(BaseModel):
    id: int
    project_id: int
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    role: str
    suspect: bool
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Design Schemas ====================


class DesignItemCreate(BaseModel):
    project_id: int
    design_id: str = Field(..., min_length=11, max_length=11)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Draft"
    priority: str = "Medium"
    design_type: str = "Architecture"
    linked_requirement_id: Optional[int] = None

    @field_validator("design_id", mode="before")
    @classmethod
    def validate_design_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="DES")


class DesignItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    design_type: Optional[str] = None
    linked_requirement_id: Optional[int] = None


class DesignItemResponse(BaseModel):
    id: int
    project_id: int
    design_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    design_type: str
    linked_requirement_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Risk Schemas ====================


class RiskItemCreate(BaseModel):
    project_id: int
    risk_id: str = Field(..., min_length=11, max_length=11)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Open"
    severity: str = "Medium"
    probability: str = "Medium"
    mitigation: Optional[str] = None
    risk_category: str = "Technical"
    linked_requirement_id: Optional[int] = None

    @field_validator("risk_id", mode="before")
    @classmethod
    def validate_risk_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="RSK")


class RiskItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    probability: Optional[str] = None
    mitigation: Optional[str] = None
    risk_category: Optional[str] = None
    linked_requirement_id: Optional[int] = None


class RiskItemResponse(BaseModel):
    id: int
    project_id: int
    risk_id: str
    title: str
    description: Optional[str] = None
    status: str
    severity: str
    probability: str
    mitigation: Optional[str] = None
    risk_category: str
    linked_requirement_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Change Request Schemas ====================


class ChangeRequestCreate(BaseModel):
    project_id: int
    change_id: str = Field(..., min_length=11, max_length=11)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Submitted"
    priority: str = "Medium"
    change_type: str = "Enhancement"
    impact_assessment: Optional[str] = None
    justification: Optional[str] = None

    @field_validator("change_id", mode="before")
    @classmethod
    def validate_change_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="CHG")


class ChangeRequestUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    change_type: Optional[str] = None
    impact_assessment: Optional[str] = None
    justification: Optional[str] = None


class ChangeRequestResponse(BaseModel):
    id: int
    project_id: int
    change_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    change_type: str
    impact_assessment: Optional[str] = None
    justification: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Defect Schemas ====================


class DefectCreate(BaseModel):
    project_id: int
    defect_id: str = Field(..., min_length=11, max_length=11)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Open"
    severity: str = "Medium"
    priority: str = "Medium"
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    owner_id: Optional[int] = None
    reporter_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    resolution_summary: Optional[str] = None
    external_tracker: Optional[str] = None
    external_repo_full_name: Optional[str] = None
    external_issue_number: Optional[int] = None
    external_issue_url: Optional[str] = None
    external_issue_state: Optional[str] = None

    @field_validator("defect_id", mode="before")
    @classmethod
    def validate_defect_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="DEF")


class DefectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    owner_id: Optional[int] = None
    reporter_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    resolution_summary: Optional[str] = None
    external_tracker: Optional[str] = None
    external_repo_full_name: Optional[str] = None
    external_issue_number: Optional[int] = None
    external_issue_url: Optional[str] = None
    external_issue_state: Optional[str] = None


class DefectResponse(BaseModel):
    id: int
    project_id: int
    defect_id: str
    title: str
    description: Optional[str] = None
    status: str
    severity: str
    priority: str
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    owner_id: Optional[int] = None
    reporter_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    resolution_summary: Optional[str] = None
    external_tracker: Optional[str] = None
    external_repo_full_name: Optional[str] = None
    external_issue_number: Optional[int] = None
    external_issue_url: Optional[str] = None
    external_issue_state: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    @field_serializer("closed_at")
    def serialize_closed_at(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Baseline Schemas ====================


class BaselineCreate(BaseModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    baseline_type: str = "Milestone"


class BaselineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    baseline_type: Optional[str] = None


class BaselineResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    status: str
    baseline_type: str
    snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Test Concept Schemas ====================


class TestConceptCreate(BaseModel):
    project_id: int
    concept_id: str = Field(..., min_length=11, max_length=11)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "Draft"
    linked_requirement_ids: List[int] = []
    coverage: float = 0

    @field_validator("concept_id", mode="before")
    @classmethod
    def validate_concept_id(cls, value: str) -> str:
        return normalize_doc_id(value, expected_type_code="TCO")


class TestConceptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    linked_requirement_ids: Optional[List[int]] = None
    coverage: Optional[float] = None


class TestConceptResponse(BaseModel):
    id: int
    project_id: int
    concept_id: str
    name: str
    description: Optional[str] = None
    status: str
    linked_requirement_ids: List[int] = []
    coverage: float
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Artefact Detail Schemas ====================


class ArtefactCommentCreate(BaseModel):
    body: str = Field(..., min_length=1)


class ArtefactCommentResponse(BaseModel):
    id: int
    artefact_type: str
    artefact_id: int
    author_name: str
    body: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class ArtefactActivityResponse(BaseModel):
    id: int
    artefact_type: str
    artefact_id: int
    event_type: str
    summary: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class ArtefactTransitionRequest(BaseModel):
    status: str = Field(..., min_length=1)


class RelatedRequirementSummary(BaseModel):
    id: int
    req_id: str
    title: str
    status: str


class RelatedTestCaseSummary(BaseModel):
    id: int
    tc_id: str
    title: str
    status: str


class RelatedDocumentSummary(BaseModel):
    id: int
    doc_id: Optional[str] = None
    title: str
    doc_type: str
    status: str
    matched_sections: List[str] = []


class RelatedProjectSummary(BaseModel):
    id: int
    name: str
    prefix: str
    status: str


class ArtefactRelatedResponse(BaseModel):
    project: RelatedProjectSummary
    linked_requirements: List[RelatedRequirementSummary] = []
    related_test_cases: List[RelatedTestCaseSummary] = []
    related_documents: List[RelatedDocumentSummary] = []


# Resolve forward references
RequirementResponse.model_rebuild()
DocumentSectionResponse.model_rebuild()
ImpactNode.model_rebuild()


class AutomatedResult(BaseModel):
    tc_id: str  # e.g., "PRJ-TC-001"
    status: str  # "Passed", "Failed", "Skipped"
    comment: Optional[str] = None
    executed_at: Optional[datetime] = None
    bud_run_id: Optional[int] = None


class SyncResultsRequest(BaseModel):
    results: List[AutomatedResult]


class SyncResultsResponse(BaseModel):
    updated: int
    not_found: List[str]


class ALMIntegrationSettings(BaseModel):
    """Schema for PLM integration settings (Bloom)."""

    bloom_url: str
    bloom_token: str
