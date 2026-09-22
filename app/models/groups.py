"""Admin-managed user groups and policies: an additive entitlement layer.

The instance roles (admin, maintainer, external) are unchanged. A Group gathers
users, carries a Policy, and is granted projects. resolve_project_role and
require_permission read the effective set; a user with no group behaves exactly
as their role does today, so this layer never regresses existing access.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Policy(Base):
    """A named permission set: a base role floor plus an (action x resource) matrix.

    The default policies (the shipped personas) carry is_default=True and are
    protected from deletion and base_role change. A policy may nest under a parent,
    inheriting then refining its matrix (deeper personas, spec'd later).
    """

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # The instance role a member behaves as for the role-based guards
    # (admin, maintainer, external). The finer gate is `permissions`.
    base_role: Mapped[str] = mapped_column(String(20), nullable=False, default="external")
    # {resource: [action, ...]} matrix, unioned with the base role's implicit set.
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Optional document-tag allow-list; generalises the external doc-type allowlist.
    doc_tag_scope: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policies.id"), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    parent: Mapped[Optional["Policy"]] = relationship(remote_side="Policy.id")


class Group(Base):
    """A named set of users that carries a policy and is granted projects."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    policy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    policy: Mapped[Optional["Policy"]] = relationship()
    members: Mapped[List["GroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    grants: Mapped[List["GroupProjectGrant"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class GroupMembership(Base):
    """A user's membership in a group."""

    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_membership_group_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    group: Mapped["Group"] = relationship(back_populates="members")


class GroupProjectGrant(Base):
    """Grants a group its policy on a project. A NULL project_id is an all-projects
    grant that covers every project, present and future."""

    __tablename__ = "group_project_grants"
    __table_args__ = (UniqueConstraint("group_id", "project_id", name="uq_group_project_grant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    group: Mapped["Group"] = relationship(back_populates="grants")
