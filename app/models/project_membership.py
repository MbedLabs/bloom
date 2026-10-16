"""
Access to a project: access entries for a user or a group, with several policies or,
for a user, the Owner role; and the project memberships with their external document
types.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProjectMembership(Base):
    """Which projects a user belongs to and at what role."""

    __tablename__ = "project_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_project_membership_user_project"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="external")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    external_doc_types: Mapped[List["ProjectExternalDocType"]] = relationship(
        back_populates="membership", cascade="all, delete-orphan"
    )


class ProjectExternalDocType(Base):
    """Doc types visible to an external user within a project."""

    __tablename__ = "project_external_doc_types"
    __table_args__ = (
        UniqueConstraint("membership_id", "doc_type", name="uq_external_doc_type_membership"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("project_memberships.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)

    membership: Mapped["ProjectMembership"] = relationship(back_populates="external_doc_types")


project_access_policies = Table(
    "project_access_policies",
    Base.metadata,
    Column(
        "access_id",
        Integer,
        ForeignKey("project_access.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("policy_id", Integer, ForeignKey("policies.id"), primary_key=True),
)


class ProjectAccess(Base):
    """One access entry on a project: a user or a group, with the Owner role (users
    only) or one or more policies."""

    __tablename__ = "project_access"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL) <> (group_id IS NULL)", name="ck_project_access_one_principal"
        ),
        UniqueConstraint("project_id", "user_id", name="uq_project_access_project_user"),
        UniqueConstraint("project_id", "group_id", name="uq_project_access_project_group"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id"), nullable=True, index=True
    )
    owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    policy_group_id: Mapped[Optional[int]] = mapped_column(ForeignKey("groups.id"), nullable=True)
    policy_group: Mapped[Optional["Group"]] = relationship(
        foreign_keys=[policy_group_id], lazy="selectin"
    )
    inherit_policies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    policies: Mapped[List["Policy"]] = relationship(
        secondary=project_access_policies, lazy="selectin"
    )
