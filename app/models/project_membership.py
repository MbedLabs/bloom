"""
Project-scoped user memberships and external role doc-type visibility.
"""

from datetime import datetime
from typing import List

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProjectMembership(Base):
    """Which projects a user belongs to and at what role.

    Admins have no rows here — their global admin role suffices.
    Maintainers must have a row per project they maintain.
    External users must have a row per project they can access."""

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
    """Doc types visible to an external user within a project.

    Only populated for memberships with role='external'.
    If empty, external user sees nothing (deny-by-default)."""

    __tablename__ = "project_external_doc_types"
    __table_args__ = (
        UniqueConstraint("membership_id", "doc_type", name="uq_external_doc_type_membership"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    membership_id: Mapped[int] = mapped_column(ForeignKey("project_memberships.id"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)

    membership: Mapped["ProjectMembership"] = relationship(back_populates="external_doc_types")
