"""
Database models for the requirements management application.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    """Project for organizing requirements and test cases."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    requirements: Mapped[List["Requirement"]] = relationship(
        back_populates="project", foreign_keys="Requirement.project_id"
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        back_populates="project", foreign_keys="TestCase.project_id"
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="project", foreign_keys="Document.project_id"
    )
    test_suites: Mapped[List["TestSuite"]] = relationship(back_populates="project")
    test_campaigns: Mapped[List["TestCampaign"]] = relationship(back_populates="project")
    design_items: Mapped[List["DesignItem"]] = relationship(
        back_populates="project", foreign_keys="DesignItem.project_id"
    )
    risk_items: Mapped[List["RiskItem"]] = relationship(
        back_populates="project", foreign_keys="RiskItem.project_id"
    )
    change_requests: Mapped[List["ChangeRequest"]] = relationship(
        back_populates="project", foreign_keys="ChangeRequest.project_id"
    )
    baselines: Mapped[List["Baseline"]] = relationship(back_populates="project")
    test_concepts: Mapped[List["TestConcept"]] = relationship(
        back_populates="project", foreign_keys="TestConcept.project_id"
    )
    defects: Mapped[List["Defect"]] = relationship(
        back_populates="project", foreign_keys="Defect.project_id"
    )
    variables: Mapped[List["ProjectVariable"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectVariable(Base):
    """Project-scoped parameters and variables for document authoring."""

    __tablename__ = "project_variables"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="variable")
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="variables")


class Requirement(Base):
    """A requirement within a project."""

    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("requirements.id"), nullable=True)
    req_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    req_type: Mapped[str] = mapped_column(String(30), default="Functional")
    req_origin: Mapped[str] = mapped_column(String(50), default="Internal")
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(
        back_populates="requirements", foreign_keys=[project_id]
    )
    parent: Mapped[Optional["Requirement"]] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Requirement"]] = relationship(back_populates="parent")
    test_run_links: Mapped[List["TestRunLink"]] = relationship(back_populates="requirement")
    outgoing_links: Mapped[List["RequirementLink"]] = relationship(
        foreign_keys="RequirementLink.source_id", back_populates="source"
    )
    incoming_links: Mapped[List["RequirementLink"]] = relationship(
        foreign_keys="RequirementLink.target_id", back_populates="target"
    )


class TestCase(Base):
    """A test case that can be linked to requirements."""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_execution_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_execution_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_bud_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(
        back_populates="test_cases", foreign_keys=[project_id]
    )
    suite_items: Mapped[List["TestSuiteItem"]] = relationship(back_populates="test_case")
    campaign_items: Mapped[List["TestCampaignItem"]] = relationship(back_populates="test_case")


class RequirementLink(Base):
    """Links between requirements for traceability (derived_from, refines, depends_on)."""

    __tablename__ = "requirement_links"
    __table_args__ = (UniqueConstraint("source_id", "target_id", "link_type", name="uq_req_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    target_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    link_type: Mapped[str] = mapped_column(String(30), default="depends_on")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source: Mapped["Requirement"] = relationship(
        foreign_keys=[source_id], back_populates="outgoing_links"
    )
    target: Mapped["Requirement"] = relationship(
        foreign_keys=[target_id], back_populates="incoming_links"
    )


class TestRunLink(Base):
    """Link from a requirement to a test run in the external test management app."""

    __tablename__ = "test_run_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    test_run_id: Mapped[int] = mapped_column(Integer, nullable=False)
    test_run_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    teststation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requirement: Mapped["Requirement"] = relationship(back_populates="test_run_links")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    doc_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(30), default="SPEC")
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="documents", foreign_keys=[project_id])
    sections: Mapped[List["DocumentSection"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSection.order",
    )


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    parent_section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("document_sections.id"), nullable=True
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_type: Mapped[str] = mapped_column(String(30), default="text")
    linked_requirement_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("requirements.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    document: Mapped["Document"] = relationship(back_populates="sections")
    parent_section: Mapped[Optional["DocumentSection"]] = relationship(
        remote_side=[id], back_populates="child_sections"
    )
    child_sections: Mapped[List["DocumentSection"]] = relationship(back_populates="parent_section")
    linked_requirement: Mapped[Optional["Requirement"]] = relationship()


class TestSuite(Base):
    """Reusable suite of test cases."""

    __tablename__ = "test_suites"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    suite_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="test_suites")
    items: Mapped[List["TestSuiteItem"]] = relationship(
        back_populates="suite", cascade="all, delete-orphan"
    )
    campaigns: Mapped[List["TestCampaign"]] = relationship(back_populates="suite")
    campaign_suites: Mapped[List["CampaignSuite"]] = relationship(back_populates="suite")


class TestSuiteItem(Base):
    """Ordered membership of a test case in a reusable suite."""

    __tablename__ = "test_suite_items"
    __table_args__ = (UniqueConstraint("suite_id", "test_case_id", name="uq_suite_tc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("test_suites.id"), nullable=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    suite: Mapped["TestSuite"] = relationship(back_populates="items")
    test_case: Mapped["TestCase"] = relationship(back_populates="suite_items")


class TestCampaign(Base):
    """A test campaign: traceability scope and execution grouping for test cases."""

    __tablename__ = "test_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    suite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("test_suites.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Planned")
    bud_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bud_run_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bud_run_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="test_campaigns")
    suite: Mapped[Optional["TestSuite"]] = relationship(back_populates="campaigns")
    items: Mapped[List["TestCampaignItem"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    campaign_suites: Mapped[List["CampaignSuite"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class TestCampaignItem(Base):
    """Individual test case execution within a campaign."""

    __tablename__ = "test_campaign_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("test_campaigns.id"), nullable=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["TestCampaign"] = relationship(back_populates="items")
    test_case: Mapped["TestCase"] = relationship(back_populates="campaign_items")


class CampaignSuite(Base):
    """Many-to-many association between campaigns and suites."""

    __tablename__ = "campaign_suites"
    __table_args__ = (UniqueConstraint("campaign_id", "suite_id", name="uq_campaign_suite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("test_campaigns.id"), nullable=False)
    suite_id: Mapped[int] = mapped_column(ForeignKey("test_suites.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["TestCampaign"] = relationship(back_populates="campaign_suites")
    suite: Mapped["TestSuite"] = relationship(back_populates="campaign_suites")


class ArtefactLink(Base):
    """Generic typed cross-artifact link foundation."""

    __tablename__ = "artefact_links"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            "target_type",
            "target_id",
            "role",
            name="uq_artefact_link",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    suspect: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DesignItem(Base):
    __tablename__ = "design_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    design_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    design_type: Mapped[str] = mapped_column(String(30), default="Architecture")
    linked_requirement_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("requirements.id"), nullable=True
    )
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(
        back_populates="design_items", foreign_keys=[project_id]
    )
    linked_requirement: Mapped[Optional["Requirement"]] = relationship()


class RiskItem(Base):
    __tablename__ = "risk_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    risk_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    probability: Mapped[str] = mapped_column(String(20), default="Medium")
    mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_category: Mapped[str] = mapped_column(String(30), default="Technical")
    linked_requirement_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("requirements.id"), nullable=True
    )
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(
        back_populates="risk_items", foreign_keys=[project_id]
    )
    linked_requirement: Mapped[Optional["Requirement"]] = relationship()


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Submitted")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    change_type: Mapped[str] = mapped_column(String(30), default="Enhancement")
    impact_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(
        back_populates="change_requests", foreign_keys=[project_id]
    )


class Baseline(Base):
    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    baseline_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    baseline_type: Mapped[str] = mapped_column(String(30), default="Milestone")
    snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="baselines")


class TestConcept(Base):
    __tablename__ = "test_concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    concept_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    linked_requirement_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    coverage: Mapped[float] = mapped_column(Float, default=0)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(
        back_populates="test_concepts", foreign_keys=[project_id]
    )


class Defect(Base):
    """A confirmed or triaged problem linked to verification, requirements, or external trackers."""

    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    defect_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    source_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reporter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_tracker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    external_repo_full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_issue_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_issue_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    external_issue_state: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    external_last_event_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="defects", foreign_keys=[project_id])


class IntegrationSetting(Base):
    """Per-project external tracker integration credentials and config."""

    __tablename__ = "integration_settings"
    __table_args__ = (
        UniqueConstraint("project_id", "tracker", name="uq_integration_project_tracker"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tracker: Mapped[str] = mapped_column(String(20), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class DefectSyncEvent(Base):
    """Append-only log of inbound/outbound sync attempts for defects."""

    __tablename__ = "defect_sync_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    tracker: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ArtefactComment(Base):
    __tablename__ = "artefact_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    artefact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    artefact_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ArtefactActivity(Base):
    __tablename__ = "artefact_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    artefact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    artefact_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
