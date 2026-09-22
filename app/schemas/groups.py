"""Pydantic schemas for the admin-managed entitlement layer: policies and groups.

See app/models/groups.py for the tables and app/core/policy_seed.py for the
shipped default policies (the personas).
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# The instance roles a policy may floor to, unchanged from the existing model.
_BASE_ROLE_PATTERN = "^(admin|maintainer|external)$"


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    base_role: str = Field(default="external", pattern=_BASE_ROLE_PATTERN)
    permissions: dict = Field(default_factory=dict)
    doc_tag_scope: Optional[List[str]] = None


class PolicyUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=500)
    base_role: Optional[str] = Field(default=None, pattern=_BASE_ROLE_PATTERN)
    permissions: Optional[dict] = None
    doc_tag_scope: Optional[List[str]] = None


class PolicyResponse(BaseModel):
    id: int
    name: str
    description: str
    base_role: str
    permissions: dict
    doc_tag_scope: Optional[List[str]] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupMemberResponse(BaseModel):
    user_id: int
    email: str
    full_name: str


class GroupGrantResponse(BaseModel):
    id: int
    # None is an all-projects grant that covers every project, present and future.
    project_id: Optional[int] = None


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    policy_id: Optional[int] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    policy_id: Optional[int] = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    policy_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    members: List[GroupMemberResponse] = Field(default_factory=list)
    grants: List[GroupGrantResponse] = Field(default_factory=list)


class GroupMemberCreate(BaseModel):
    user_id: int


class GroupGrantCreate(BaseModel):
    # Omit or null to grant every project (present and future).
    project_id: Optional[int] = None
