"""Controlled document workflow cycles, immutable revisions and delivery recipients."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base

SET_NULL = "SET NULL"
USERS_ID = "users.id"


class ArtefactWorkflow(Base):
    """Current controlled revision, its assignee and equivalent reviewer assignments for an
    artefact."""

    __tablename__ = "artefact_workflows"
    __table_args__ = (
        UniqueConstraint("artefact_type", "artefact_id", name="uq_artefact_workflow"),
        CheckConstraint(
            "phase IN ('Draft', 'Review', 'Approval', 'Approved')",
            name="ck_artefact_workflow_phase",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete=SET_NULL), nullable=True
    )
    artefact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    artefact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    revision_creator_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    phase: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft")
    authorizing_change_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("change_requests.id", ondelete=SET_NULL), nullable=True
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    approver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    review_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ArtefactRevision(Base):
    """Immutable approved content with the signoff provenance actually recorded."""

    __tablename__ = "artefact_revisions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "revision_number", name="uq_artefact_revision"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("artefact_workflows.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    authorizing_change_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("change_requests.id", ondelete=SET_NULL), nullable=True
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    approver_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ArtefactRequest(Base):
    """One review or approval handoff for exact content in a workflow revision."""

    __tablename__ = "artefact_requests"
    __table_args__ = (
        CheckConstraint("kind IN ('review', 'approval')", name="ck_artefact_request_kind"),
        CheckConstraint(
            "status IN ('pending', 'answered', 'declined', 'superseded')",
            name="ck_artefact_request_status",
        ),
        Index(
            "uq_artefact_requests_pending_cycle",
            "workflow_id",
            "revision_number",
            "kind",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("artefact_workflows.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    requester_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete="CASCADE"), nullable=True
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    decided_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ArtefactRequestRecipient(Base):
    """The eligible users selected for a handoff's original delivery."""

    __tablename__ = "artefact_request_recipients"

    request_id: Mapped[int] = mapped_column(
        ForeignKey("artefact_requests.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID, ondelete="CASCADE"), primary_key=True)


class ArtefactRevisionFile(Base):
    """Immutable approved attachment metadata and a retained storage reference."""

    __tablename__ = "artefact_revision_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("artefact_revisions.id"), nullable=False)
    attachment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


@event.listens_for(Session, "before_flush")
def _guard_workflow_writes(session, flush_context, instances) -> None:
    """Check controlled authoring and archived content before ORM writes."""
    from app.services.document_workflow import guard_workflow_writes

    guard_workflow_writes(session)


@event.listens_for(Session, "after_transaction_end")
def _clear_workflow_lookups(session, transaction) -> None:
    """Release cached guard lookups after the session transaction ends."""
    if transaction.parent is None:
        session.info.pop("workflow_lookup_cache", None)
