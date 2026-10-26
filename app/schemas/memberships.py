"""
Pydantic schemas for project-scoped user membership management.

EXTERNAL_DOC_TYPES mirrors the DocType union in ui/src/types/doc.ts; DEFAULT_EXTERNAL_DOC_TYPES are
the types an external member sees when a membership names no doc_types.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

EXTERNAL_DOC_TYPES = {
    "REQ",
    "SPEC",
    "TC",
    "DES",
    "RSK",
    "CHG",
    "CPT",
    "DEF",
    "CMP",
    "TS",
    "PRT",
    "RPT",
    "STD",
}

DEFAULT_EXTERNAL_DOC_TYPES = {"REQ", "TC", "CPT", "CMP"}


class ProjectMembershipExternalDocType(BaseModel):
    doc_type: str = Field(..., min_length=2, max_length=10)


class ProjectMembershipBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(gt=0)
    owner: bool = False
    inherit_policies: bool = False
    policy_ids: list[int] = Field(default_factory=list)
    policy_group_id: Optional[int] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valid_access(self):
        """Require Owner or a nonempty distinct selection of policies."""
        validate_entry(self.owner, self.policy_ids, self.inherit_policies, self.policy_group_id)
        return self


class ProjectMembershipCreate(ProjectMembershipBase):
    """A direct user entry with Owner or selected policies."""


class ProjectMembershipUpdate(BaseModel):
    """Changes to the Owner flag and policy selection of a direct entry."""

    model_config = ConfigDict(extra="forbid")
    owner: Optional[bool] = None
    inherit_policies: Optional[bool] = None
    policy_ids: Optional[list[int]] = None
    policy_group_id: Optional[int] = Field(default=None, gt=0)


def validate_entry(
    owner: bool,
    policy_ids: list[int],
    inherit_policies: bool = False,
    policy_group_id: Optional[int] = None,
) -> None:
    """Require a direct Owner entry or a distinct positive policy selection."""
    if policy_group_id is not None:
        if policy_group_id <= 0 or owner or inherit_policies or policy_ids:
            raise ValueError("Choose a project policy group without another access mode")
        return
    if owner and (policy_ids or inherit_policies) or inherit_policies and policy_ids:
        raise ValueError("Choose Owner, inherited group policies or explicit policies")
    if not owner and not inherit_policies and not policy_ids:
        raise ValueError("Choose inherited group policies or one or more explicit policies")
    if any(value <= 0 for value in policy_ids) or len(set(policy_ids)) != len(policy_ids):
        raise ValueError("Choose distinct positive policy identifiers")


class ProjectMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    project_id: int
    owner: bool
    inherit_policies: bool
    policy_ids: list[int]
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        """Serialize a stored UTC timestamp with the UTC designator."""
        return f"{dt.isoformat()}Z"


class ProjectMemberResponse(BaseModel):
    """A direct project entry with user details and explicit authority."""

    id: int
    user_id: int
    email: str
    full_name: str
    profile_picture_url: str | None = None
    owner: bool
    inherit_policies: bool
    policy_ids: list[int]
    policy_group_id: Optional[int] = None
    policy_group_name: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        """Serialize a stored UTC timestamp with the UTC designator."""
        return f"{dt.isoformat()}Z"


class UserProjectAccess(BaseModel):
    """One project a user has access to, with the groups that give it."""

    project_id: int
    project_name: str
    owner: bool
    groups: list[str]
    direct: bool


class UserAccessSummary(BaseModel):
    """A user's groups and project access by name, without policies or permissions."""

    every_project: bool
    groups: list[str]
    projects: list[UserProjectAccess]
