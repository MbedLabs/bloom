"""Scoped policy rules, group-owned policy sets and separate memberships."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class NamedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before", check_fields=False)
    @classmethod
    def trim_name(cls, value):
        """Trim surrounding whitespace before validating a name."""
        return value.strip() if isinstance(value, str) else value


class PolicyRule(BaseModel):
    """Independent permissions and the document origins covered by one rule."""

    model_config = ConfigDict(extra="forbid")
    read: bool = False
    write: bool = False
    review: bool = False
    approve: bool = False
    delete: bool = False
    all_origins: bool = False
    visibility: list[Literal["internal", "customer"]] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)


class PolicyRuleResponse(PolicyRule):
    """A rule with the actions it grants."""

    model_config = ConfigDict(extra="ignore")
    actions: list[str] = Field(default_factory=list)


class PolicyCreate(NamedInput):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    scope: Literal["document", "project", "app"] = "project"
    rules: dict[str, PolicyRule] = Field(default_factory=dict)


class PolicyUpdate(NamedInput):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    scope: Optional[Literal["document", "project", "app"]] = None
    rules: Optional[dict[str, PolicyRule]] = None


class PolicyResponse(BaseModel):
    id: int
    name: str
    description: str
    scope: Literal["document", "project", "app"]
    rules: dict[str, PolicyRuleResponse]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        """Serialize stored UTC timestamps with the UTC designator."""
        return f"{dt.isoformat()}Z" if dt else None


class GroupMemberResponse(BaseModel):
    user_id: int
    email: str
    full_name: str


class GroupGrantResponse(BaseModel):
    id: int
    project_id: int


class GroupCreate(NamedInput):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    policy_ids: list[int] = Field(default_factory=list)

    @field_validator("policy_ids")
    @classmethod
    def distinct_policies(cls, value):
        """Require distinct positive policy identifiers."""
        if any(item <= 0 for item in value) or len(set(value)) != len(value):
            raise ValueError("Choose distinct positive policy identifiers")
        return sorted(value)


class GroupUpdate(NamedInput):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    description: Optional[str] = Field(default=None, max_length=500)
    policy_ids: Optional[list[int]] = None

    @field_validator("policy_ids")
    @classmethod
    def distinct_policies(cls, value):
        """Require distinct positive policy identifiers when supplied."""
        if value is not None and (
            any(item <= 0 for item in value) or len(set(value)) != len(value)
        ):
            raise ValueError("Choose distinct positive policy identifiers")
        return sorted(value) if value is not None else None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str
    policy_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    members: list[GroupMemberResponse] = Field(default_factory=list)
    grants: list[GroupGrantResponse] = Field(default_factory=list)

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: Optional[datetime], _info):
        """Serialize stored UTC timestamps with the UTC designator."""
        return f"{dt.isoformat()}Z" if dt else None


class GroupMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int = Field(gt=0)


class GroupMembersCreate(BaseModel):
    """A nonempty selection of distinct users to add together."""

    model_config = ConfigDict(extra="forbid")
    user_ids: list[int] = Field(min_length=1)

    @field_validator("user_ids")
    @classmethod
    def distinct_users(cls, value):
        """Require distinct positive user identifiers."""
        if any(item <= 0 for item in value) or len(set(value)) != len(value):
            raise ValueError("Choose distinct positive user identifiers")
        return sorted(value)


class GroupGrantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inherit_policies: Literal[True] = True


class GroupGrantCreate(GroupGrantUpdate):
    project_id: int = Field(gt=0)


class GroupAssignmentCreate(GroupMembersCreate):
    """Users receiving this bundle on one project."""

    project_id: int = Field(gt=0)
