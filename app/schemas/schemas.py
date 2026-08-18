"""
Pydantic schemas for API request/response validation.
"""

import re
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

T = TypeVar("T")


class StrictModel(BaseModel):
    """Base model that forbids extra fields — user-supplied IDs get rejected loudly."""

    model_config = ConfigDict(extra="forbid")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


# ==================== Project Schemas ====================

PROJECT_PREFIX_PATTERN = re.compile(r"^[A-Z]{3}$")
ARTEFACT_VISIBILITY_PATTERN = r"^(internal|customer)$"
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


class ProjectCreate(StrictModel):
    """Schema for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    prefix: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = None
    status: str = "Active"

    @field_validator("prefix", mode="before")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        return normalize_project_prefix(value)


class ProjectUpdate(StrictModel):
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
    campaign_count: int = 0
    design_count: int = 0
    risk_count: int = 0
    change_count: int = 0
    test_concept_count: int = 0
    test_suite_count: int = 0
    defect_count: int = 0
    coverage_percent: float = 0
    uncovered_requirement_count: int = 0

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


class ProjectVariableCreate(StrictModel):
    project_id: int
    kind: str = Field(default="variable", pattern="^(parameter|variable)$")
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1)
    description: Optional[str] = None


class ProjectVariableUpdate(StrictModel):
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
    last_execution_status: Optional[str] = None
    last_executed_at: Optional[datetime] = None
    last_bud_run_id: Optional[int] = None

    @field_serializer("last_executed_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None


class TestCampaignSummary(BaseModel):
    id: int
    campaign_id: str
    name: str
    status: str
    last_execution_status: Optional[str] = None
    last_executed_at: Optional[datetime] = None

    @field_serializer("last_executed_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None


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


class RequirementCreate(StrictModel):
    """Schema for creating a requirement."""

    project_id: int
    parent_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Draft"
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    priority: str = "Medium"
    req_type: str = "Functional"
    req_origin: str = "Internal"
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class RequirementUpdate(StrictModel):
    """Schema for updating a requirement."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
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
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class RequirementResponse(BaseModel):
    """Schema for requirement response."""

    id: int
    project_id: int
    parent_id: Optional[int] = None
    req_id: str
    title: str
    description: Optional[str] = None
    status: str
    visibility: str = "internal"
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
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

    @field_serializer("created_at", "updated_at", "reviewed_at", "approved_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


# ==================== TestCase Schemas ====================


class TestCaseCreate(StrictModel):
    """Schema for creating a test case."""

    project_id: int
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    status: str = "Draft"
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class TestCaseUpdate(StrictModel):
    """Schema for updating a test case."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
    reviewer_id: Optional[int] = None
    approver_id: Optional[int] = None
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


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
    visibility: str = "internal"
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
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

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


class TestRunLinkCreate(StrictModel):
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
    """Schema for the liveness probe response."""

    status: str = "healthy"
    version: str
    # Liveness never inspects the database, so it must not claim a connection it
    # has not verified. The real dependency check lives at /api/ready.
    database: str = "not_checked"


class ReadinessResponse(BaseModel):
    """Schema for the readiness probe response (database verified via SELECT 1)."""

    status: str = "ready"
    version: str
    database: str = "connected"


class VersionResponse(BaseModel):
    """Schema for version response."""

    version: str
    api_version: str = "v1"


class DocumentCreate(StrictModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=500)
    doc_type: str = Field(default="SPEC", pattern="^(SPEC|PRT|RPT|STD)$")
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    description: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class DocumentUpdate(StrictModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    doc_type: Optional[str] = Field(None, pattern="^(SPEC|PRT|RPT|STD)$")
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
    status: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class DocumentSectionCreate(StrictModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: Optional[str] = None
    section_type: str = "text"
    order: int = 0
    parent_section_id: Optional[int] = None


class DocumentSectionUpdate(StrictModel):
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


class TestReportFile(BaseModel):
    """One file of a published test report, base64 encoded."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=100)
    content_base64: str


class TestReportPublish(BaseModel):
    """A Bud run's report, published into a project as a Report document."""

    project_prefix: str = Field(..., min_length=1, max_length=20)
    bud_run_id: int
    run_name: str = Field(..., min_length=1, max_length=400)
    status: Optional[str] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    executed_at: Optional[datetime] = None
    run_url: Optional[str] = Field(default=None, max_length=500)
    tc_ids: List[str] = Field(default_factory=list)
    files: List[TestReportFile] = Field(default_factory=list)


class TestReportPublishResponse(BaseModel):
    document_id: int
    doc_id: Optional[str] = None
    created: bool
    attachment_ids: List[int] = Field(default_factory=list)


class DocumentAttachmentResponse(BaseModel):
    """A file held against a document."""

    id: int
    document_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    source_ref: Optional[str] = None
    uploaded_by_id: Optional[int] = None
    created_at: datetime

    @field_serializer("created_at")
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
    visibility: str = "internal"
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
    visibility: str = "internal"
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


class TestSuiteCreate(StrictModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "Draft"
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    test_case_ids: List[int] = []


class TestSuiteUpdate(StrictModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)


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
    visibility: str = "internal"
    created_at: datetime
    updated_at: datetime
    total_items: int = 0
    last_execution_status: Optional[str] = None
    last_executed_at: Optional[datetime] = None
    last_bud_run_id: Optional[int] = None

    @field_serializer("created_at", "updated_at", "last_executed_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        return f"{dt.isoformat()}Z" if dt else None

    class Config:
        from_attributes = True


class TestSuiteDetailResponse(TestSuiteResponse):
    items: List[TestSuiteItemResponse] = []
    related_requirements: List[RequirementSummary] = []
    linked_campaigns: List[TestCampaignSummary] = []
    related_concepts: List[TestConceptSummary] = []


class TestCampaignCreate(StrictModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    suite_id: Optional[int] = None
    suite_ids: List[int] = []
    bud_run_id: Optional[int] = None
    bud_run_url: Optional[str] = None
    bud_run_status: Optional[str] = None
    test_case_ids: List[int] = []


class TestCampaignUpdate(StrictModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
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
    campaign_id: str
    suite_id: Optional[int] = None
    bud_run_id: Optional[int] = None
    bud_run_url: Optional[str] = None
    bud_run_status: Optional[str] = None
    name: str
    description: Optional[str] = None
    status: str
    visibility: str = "internal"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    total_items: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    pending: int = 0
    last_execution_status: Optional[str] = None
    last_executed_at: Optional[datetime] = None
    suite: Optional[TestSuiteSummary] = None
    suites: List[TestSuiteSummary] = []

    @field_serializer("started_at", "completed_at", "created_at", "updated_at", "last_executed_at")
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


class TestCampaignItemUpdate(StrictModel):
    comment: Optional[str] = None


class ArtefactLinkCreate(StrictModel):
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


class DesignItemCreate(StrictModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Draft"
    priority: str = "Medium"
    design_type: str = "Architecture"
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class DesignItemUpdate(StrictModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    design_type: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class DesignItemResponse(BaseModel):
    id: int
    project_id: int
    design_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    design_type: str
    visibility: str = "internal"
    created_at: datetime
    updated_at: datetime
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Risk Schemas ====================


class RiskItemCreate(StrictModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Open"
    severity: str = "Medium"
    probability: str = "Medium"
    mitigation: Optional[str] = None
    risk_category: str = "Technical"
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class RiskItemUpdate(StrictModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    probability: Optional[str] = None
    mitigation: Optional[str] = None
    risk_category: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


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
    visibility: str = "internal"
    created_at: datetime
    updated_at: datetime
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Change Request Schemas ====================


class ChangeRequestCreate(StrictModel):
    project_id: int
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Submitted"
    priority: str = "Medium"
    change_type: str = "Enhancement"
    impact_assessment: Optional[str] = None
    justification: Optional[str] = None
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    external_tracker: Optional[str] = None
    external_repo_full_name: Optional[str] = None
    external_issue_number: Optional[int] = None
    external_issue_url: Optional[str] = None
    external_issue_state: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class ChangeRequestUpdate(StrictModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    change_type: Optional[str] = None
    impact_assessment: Optional[str] = None
    justification: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
    external_tracker: Optional[str] = None
    external_repo_full_name: Optional[str] = None
    external_issue_number: Optional[int] = None
    external_issue_url: Optional[str] = None
    external_issue_state: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


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
    visibility: str = "internal"
    external_tracker: Optional[str] = None
    external_repo_full_name: Optional[str] = None
    external_issue_number: Optional[int] = None
    external_issue_url: Optional[str] = None
    external_issue_state: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Defect Schemas ====================


class DefectCreate(StrictModel):
    project_id: int
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
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)


class DefectUpdate(StrictModel):
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
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)


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
    visibility: str = "internal"
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


class BaselineCreate(StrictModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    baseline_type: str = "Milestone"


class BaselineUpdate(StrictModel):
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


class TestConceptCreate(StrictModel):
    project_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "Draft"
    coverage: float = 0
    visibility: str = Field(default="internal", pattern=ARTEFACT_VISIBILITY_PATTERN)
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class TestConceptUpdate(StrictModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    coverage: Optional[float] = None
    visibility: Optional[str] = Field(default=None, pattern=ARTEFACT_VISIBILITY_PATTERN)
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None


class TestConceptResponse(BaseModel):
    id: int
    project_id: int
    concept_id: str
    name: str
    description: Optional[str] = None
    status: str
    visibility: str = "internal"
    linked_requirement_ids: List[int] = []
    coverage: float
    created_at: datetime
    updated_at: datetime
    content_json: Optional[Dict[str, Any]] = None
    content_html: Optional[str] = None

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime, _info):
        return f"{dt.isoformat()}Z"

    class Config:
        from_attributes = True


# ==================== Artefact Detail Schemas ====================


class ArtefactCommentCreate(StrictModel):
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
    tc_id: str = Field(min_length=1, max_length=100)  # e.g., "PRJ-TC-001"
    status: str  # "Passed", "Failed", "Skipped"
    comment: Optional[str] = None
    executed_at: Optional[datetime] = None
    bud_run_id: Optional[int] = None


class SyncResultsRequest(BaseModel):
    results: List[AutomatedResult] = Field(min_length=1, max_length=1000)


class SyncResultsResponse(BaseModel):
    updated: int
    not_found: List[str]


class ALMIntegrationSettings(BaseModel):
    """Schema for PLM integration settings (Bloom)."""

    bloom_url: str
    bloom_token: str
