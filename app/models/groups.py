"""Admin-managed policies and groups.

A Policy defines operations and origins; a Group owns a named set of policies.
Project entries assign bundles to users. Earlier global memberships are retained.
"""

from datetime import datetime
from typing import List

from sqlalchemy import (
    JSON,
    Boolean,
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

group_policies = Table(
    "group_policies",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("policy_id", Integer, ForeignKey("policies.id"), primary_key=True),
)

user_application_policies = Table(
    "user_application_policies",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("policy_id", Integer, ForeignKey("policies.id"), primary_key=True),
)


class Policy(Base):
    """A named permission set: per resource, the actions it grants (stored as an
    (action x resource) matrix and shown as Read or Write), and per document type the tags
    it covers.

    ``type_tags`` maps a document type to ``{"visibility": [...], "tags": [...]}``: the
    built-in visibility tags (``internal``, ``customer``) and the ids of further tags. The
    shipped defaults carry is_default=True and are read-only.
    """

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="project")
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    type_tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Group(Base):
    """A named bundle of policies assignable to users on individual projects."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    members: Mapped[List["GroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    policies: Mapped[List[Policy]] = relationship(secondary=group_policies, lazy="selectin")


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
