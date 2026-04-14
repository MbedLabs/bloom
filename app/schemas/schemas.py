"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== Project Schemas ====================

class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    name: str = Field(..., min_length=1, max_length=255)
    prefix: str = Field(..., min_length=1, max_length=10)
    description: Optional[str] = None
    status: str = "Active"


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    prefix: Optional[str] = Field(None, min_length=1, max_length=10)
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: int
    name: str
    prefix: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    requirement_count: int = 0
    test_case_count: int = 0

    class Config:
        from_attributes = True


# ==================== Requirement Schemas ====================

class RequirementCreate(BaseModel):
    """Schema for creating a requirement."""
    project_id: int
    parent_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = "Draft"
    priority: str = "Medium"
    req_type: str = "Functional"


class RequirementUpdate(BaseModel):
    """Schema for updating a requirement."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    req_type: Optional[str] = None
    parent_id: Optional[int] = None


class RequirementResponse(BaseModel):
    """Schema for requirement response."""
    id: int
    project_id: int
    parent_id: Optional[int]
    req_id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    req_type: str
    created_at: datetime
    updated_at: datetime
    children: List["RequirementResponse"] = []
    test_case_count: int = 0

    class Config:
        from_attributes = True


# ==================== TestCase Schemas ====================

class TestCaseCreate(BaseModel):
    """Schema for creating a test case."""
    project_id: int
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    status: str = "Draft"


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = None


class TestCaseResponse(BaseModel):
    """Schema for test case response."""
    id: int
    project_id: int
    tc_id: str
    title: str
    description: Optional[str]
    preconditions: Optional[str]
    steps: Optional[List[Dict[str, Any]]]
    status: str
    created_at: datetime
    updated_at: datetime
    requirement_count: int = 0

    class Config:
        from_attributes = True


# ==================== RequirementTestCase Schemas ====================

class RequirementTestCaseCreate(BaseModel):
    """Schema for linking a test case to a requirement."""
    test_case_id: int


class RequirementTestCaseResponse(BaseModel):
    """Schema for requirement-test case link response."""
    id: int
    requirement_id: int
    test_case_id: int
    created_at: datetime

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
    test_run_name: Optional[str]
    teststation_url: Optional[str]
    status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Traceability Schemas ====================

class TraceabilityItem(BaseModel):
    """Schema for a single item in the traceability matrix."""
    requirement: RequirementResponse
    linked_test_cases: List[TestCaseResponse]
    linked_test_runs: List[TestRunLinkResponse]
    coverage_status: str


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


# Resolve forward references
RequirementResponse.model_rebuild()
