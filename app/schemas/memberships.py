"""
Pydantic schemas for project-scoped user membership management.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.user import UserRole

# ── Doc types exposed to external visibility configuration ──────────────
# Mirrors the UI DocType union in ui/src/types/doc.ts
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

# Default doc types visible to external users when an admin creates a
# membership without specifying doc_types.
DEFAULT_EXTERNAL_DOC_TYPES = {"REQ", "TC", "CPT", "CMP"}


class ProjectMembershipExternalDocType(BaseModel):
    doc_type: str = Field(..., min_length=2, max_length=10)


class ProjectMembershipBase(BaseModel):
    user_id: int
    role: str = Field(default="external", pattern="^(maintainer|external)$")


class ProjectMembershipCreate(ProjectMembershipBase):
    """Paylod for adding a user to a project.

    For external role, doc_types can optionally be provided.
    If omitted and role='external', the default set is applied.
    """

    doc_types: Optional[List[str]] = Field(
        default=None,
        description="Doc types visible to this external user. Ignored for maintainers.",
    )


class ProjectMembershipUpdate(BaseModel):
    """Payload for updating a project membership.

    Only the role and/or doc_types can be changed.
    user_id and project_id are immutable (delete and re-create if needed)."""

    role: Optional[str] = Field(default=None, pattern="^(maintainer|external)$")
    doc_types: Optional[List[str]] = Field(
        default=None,
        description="Doc types visible to this external user. Replaces existing set.",
    )


class ProjectMembershipResponse(BaseModel):
    id: int
    user_id: int
    project_id: int
    role: str
    doc_types: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectMemberResponse(BaseModel):
    """A project member with user details + membership info."""

    id: int
    user_id: int
    email: str
    full_name: str
    role: str
    doc_types: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
