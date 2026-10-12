"""The instance tag base and the tags carried by artefacts."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.models import (
    ChangeRequest,
    Defect,
    DesignItem,
    Document,
    Requirement,
    RiskItem,
    TestCampaign,
    TestCase,
    TestConcept,
    TestSuite,
)


class Tag(Base):
    """One tag of the instance tag base, managed by administrators."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ArtefactTag(Base):
    """A tag carried by one artefact."""

    __tablename__ = "artefact_tags"
    __table_args__ = (
        UniqueConstraint("tag_id", "artefact_type", "artefact_id", name="uq_artefact_tag"),
        Index("ix_artefact_tags_artefact", "artefact_type", "artefact_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False, index=True)
    artefact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    artefact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


TAGGED_MODELS = {
    "requirement": Requirement,
    "test-case": TestCase,
    "document": Document,
    "design": DesignItem,
    "risk": RiskItem,
    "change": ChangeRequest,
    "test-concept": TestConcept,
    "defect": Defect,
    "test-suite": TestSuite,
    "campaign": TestCampaign,
}
TAG_TYPE_OF_MODEL = {model: key for key, model in TAGGED_MODELS.items()}

TYPE_CODES = {
    "requirement": "REQ",
    "test-case": "TC",
    "document": None,
    "design": "DES",
    "risk": "RSK",
    "change": "CHG",
    "test-concept": "CPT",
    "defect": "DEF",
    "test-suite": "TS",
    "campaign": "CMP",
}
