"""
Database models for the requirements management application.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.link_rules import allowed_link_triples

ALL_DELETE_ORPHAN = "all, delete-orphan"
PROJECTS_ID = "projects.id"
REQUIREMENTS_ID = "requirements.id"
TEST_SUITES_ID = "test_suites.id"

SET_NULL = "SET NULL"
USERS_ID = "users.id"


class ArtefactVisibility(str, Enum):
    internal = "internal"
    customer = "customer"


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
        back_populates="project", cascade=ALL_DELETE_ORPHAN
    )


class ProjectVariable(Base):
    """Project-scoped parameters and variables for document authoring."""

    __tablename__ = "project_variables"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(REQUIREMENTS_ID), nullable=True, index=True
    )
    req_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    req_type: Mapped[str] = mapped_column(String(30), default="Functional")
    req_origin: Mapped[str] = mapped_column(String(50), default="Internal")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    tc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_execution_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_execution_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_bud_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
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
    source_id: Mapped[int] = mapped_column(ForeignKey(REQUIREMENTS_ID), nullable=False)
    target_id: Mapped[int] = mapped_column(ForeignKey(REQUIREMENTS_ID), nullable=False)
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
    requirement_id: Mapped[int] = mapped_column(ForeignKey(REQUIREMENTS_ID), nullable=False)
    test_run_id: Mapped[int] = mapped_column(Integer, nullable=False)
    test_run_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    teststation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requirement: Mapped["Requirement"] = relationship(back_populates="test_run_links")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    doc_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(30), default="SPEC")
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="documents", foreign_keys=[project_id])
    sections: Mapped[List["DocumentSection"]] = relationship(
        back_populates="document",
        cascade=ALL_DELETE_ORPHAN,
        order_by="DocumentSection.order",
    )
    attachments: Mapped[List["DocumentAttachment"]] = relationship(
        back_populates="document",
        cascade=ALL_DELETE_ORPHAN,
        order_by="DocumentAttachment.created_at",
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
        ForeignKey(REQUIREMENTS_ID), nullable=True
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    suite_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    project: Mapped["Project"] = relationship(back_populates="test_suites")
    items: Mapped[List["TestSuiteItem"]] = relationship(
        back_populates="suite", cascade=ALL_DELETE_ORPHAN
    )
    campaigns: Mapped[List["TestCampaign"]] = relationship(back_populates="suite")
    campaign_suites: Mapped[List["CampaignSuite"]] = relationship(back_populates="suite")


class TestSuiteItem(Base):
    """Ordered membership of a test case in a reusable suite."""

    __tablename__ = "test_suite_items"
    __table_args__ = (UniqueConstraint("suite_id", "test_case_id", name="uq_suite_tc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey(TEST_SUITES_ID), nullable=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    suite: Mapped["TestSuite"] = relationship(back_populates="items")
    test_case: Mapped["TestCase"] = relationship(back_populates="suite_items")


class TestCampaign(Base):
    """A test campaign: traceability scope and execution grouping for test cases."""

    __tablename__ = "test_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    suite_id: Mapped[Optional[int]] = mapped_column(ForeignKey(TEST_SUITES_ID), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Planned")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
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
        back_populates="campaign", cascade=ALL_DELETE_ORPHAN
    )
    campaign_suites: Mapped[List["CampaignSuite"]] = relationship(
        back_populates="campaign", cascade=ALL_DELETE_ORPHAN
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
    suite_id: Mapped[int] = mapped_column(ForeignKey(TEST_SUITES_ID), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["TestCampaign"] = relationship(back_populates="campaign_suites")
    suite: Mapped["TestSuite"] = relationship(back_populates="campaign_suites")


class AllowedLinkTriple(Base):
    """Storage triples accepted for typed artefact links."""

    __tablename__ = "allowed_link_triples"

    source_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), primary_key=True)


@event.listens_for(AllowedLinkTriple.__table__, "after_create")
def _seed_allowed_link_triples(table, connection, **kwargs) -> None:
    """Seed allowed triples when ORM metadata creates a new table."""
    connection.execute(
        table.insert(),
        [
            dict(zip(("source_type", "target_type", "role"), triple))
            for triple in allowed_link_triples()
        ],
    )


class ArtefactLink(Base):
    """Generic typed cross-artifact link foundation."""

    __tablename__ = "artefact_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_type", "target_type", "role"],
            [
                "allowed_link_triples.source_type",
                "allowed_link_triples.target_type",
                "allowed_link_triples.role",
            ],
            name="fk_artefact_links_allowed_triple",
            postgresql_not_valid=True,
        ).ddl_if(dialect="postgresql"),
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    design_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    design_type: Mapped[str] = mapped_column(String(30), default="Architecture")
    linked_requirement_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(REQUIREMENTS_ID), nullable=True
    )
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    risk_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    probability: Mapped[str] = mapped_column(String(20), default="Medium")
    mitigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_category: Mapped[str] = mapped_column(String(30), default="Technical")
    linked_requirement_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(REQUIREMENTS_ID), nullable=True
    )
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
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
    """A change request. The external_* columns link it to an issue in GitHub, GitLab or Jira; inbound
    webhooks look it up by tracker, repository and issue number.
    """

    __tablename__ = "change_requests"
    __table_args__ = (
        Index(
            "ix_change_requests_external_issue",
            "external_tracker",
            "external_repo_full_name",
            "external_issue_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    change_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    change_type: Mapped[str] = mapped_column(String(30), default="Enhancement")
    impact_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_tracker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    external_repo_full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_issue_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_issue_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    external_issue_state: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    external_last_event_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False, index=True)
    concept_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    linked_requirement_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    coverage: Mapped[float] = mapped_column(Float, default=0)
    source_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_project_id: Mapped[Optional[int]] = mapped_column(ForeignKey(PROJECTS_ID), nullable=True)
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
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False)
    defect_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    visibility: Mapped[str] = mapped_column(String(20), default=ArtefactVisibility.internal.value)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    source_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reporter_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    resolution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_tracker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    external_repo_full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_issue_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_issue_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    external_issue_state: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    external_issue_closed: Mapped[Optional[bool]] = mapped_column(nullable=True)
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
    """Per-project external tracker integration credentials and config.

    account_email is the Jira Cloud account that owns the API token (Basic auth `email:api_token`).
    webhook_secret holds a Fernet envelope (Text). jira_project_key is the Jira project key this
    integration owns, unique across Jira integrations, and with create_defects_on_inbound an inbound
    Jira issue without a matching defect creates one. GitHub and GitLab leave the Jira columns
    unused. The sync_* columns record the scheduled sync: last attempt and last success, the
    last failure and the repositories the last run skipped, the counts of the last run, whether
    a full Jira creation search is pending and where a capped one continues, and the issue
    number the deletion check reached.
    """

    __tablename__ = "integration_settings"
    __table_args__ = (
        UniqueConstraint("project_id", "tracker", name="uq_integration_project_tracker"),
        UniqueConstraint("tracker", "jira_project_key", name="uq_integration_jira_project_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECTS_ID), nullable=False)
    tracker: Mapped[str] = mapped_column(String(20), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    account_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jira_project_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    create_defects_on_inbound: Mapped[bool] = mapped_column(default=True)
    jira_issue_types: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    jira_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    jira_jql: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jira_reference_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jira_priority_map: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    two_way: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    sync_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_created: Mapped[int] = mapped_column(default=0)
    sync_updated: Mapped[int] = mapped_column(default=0)
    sync_full_scan: Mapped[bool] = mapped_column(default=True)
    sync_scan_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sync_removal_cursor: Mapped[int] = mapped_column(default=0)
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


class ChangeRequestSyncEvent(Base):
    """Append-only log of inbound/outbound sync attempts for change requests."""

    __tablename__ = "change_request_sync_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_request_id: Mapped[int] = mapped_column(
        ForeignKey("change_requests.id"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    tracker: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebhookDelivery(Base):
    """Authenticated delivery ledger for replay and rolling-rate protection."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("tracker", "delivery_id", name="uq_webhook_tracker_delivery"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_setting_id: Mapped[int] = mapped_column(
        ForeignKey("integration_settings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tracker: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(255), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ServiceCredential(Base):
    """Opaque, hashed, single-purpose machine credential."""

    __tablename__ = "service_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), nullable=False)


class ArtefactComment(Base):
    """A comment on an artefact. A reply points to the first comment of its thread; a
    thread's first comment may quote the passage it is about (text before, the passage and
    text after) and records when and by whom the thread was resolved."""

    __tablename__ = "artefact_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    artefact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    artefact_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    revision_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    review_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("artefact_requests.id", ondelete=SET_NULL), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("artefact_comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    anchor_exact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anchor_prefix: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    anchor_suffix: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ArtefactActivity(Base):
    __tablename__ = "artefact_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    artefact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    artefact_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """An in-app notification addressed to one user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), nullable=False, index=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(USERS_ID, ondelete=SET_NULL), nullable=True
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(PROJECTS_ID), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ImportAttempt(Base):
    """Persistent ReqIF import lease and rolling rate-limit record."""

    __tablename__ = "import_attempts"
    __table_args__ = (
        Index(
            "uq_import_attempts_active_project",
            "project_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(USERS_ID), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey(PROJECTS_ID, ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class DocumentAttachment(Base):
    """A file held against a document.

    source_ref is set for a file delivered by an external system; a second delivery with the same
    source_ref replaces the file.
    """

    __tablename__ = "document_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey(USERS_ID), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    document: Mapped["Document"] = relationship(back_populates="attachments")


class AttachmentUploadLease(Base):
    """One active interactive attachment upload for a Bloom user."""

    __tablename__ = "attachment_upload_leases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(USERS_ID, ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class AttachmentUploadAttempt(Base):
    """Rolling interactive attachment-upload start record."""

    __tablename__ = "attachment_upload_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(USERS_ID, ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CompanyLogo(Base):
    """Instance-wide company logo: an admin-uploaded customer logo for PDF reports."""

    __tablename__ = "company_logo"

    id: Mapped[int] = mapped_column(primary_key=True)
    logo: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    logo_content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    logo_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


ARTEFACT_MODELS = (
    Requirement,
    TestCase,
    Document,
    TestSuite,
    TestCampaign,
    DesignItem,
    RiskItem,
    ChangeRequest,
    TestConcept,
    Defect,
)
