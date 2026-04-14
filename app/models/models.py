"""
Database models for the requirements management application.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON, UniqueConstraint
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
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    requirements: Mapped[List["Requirement"]] = relationship(back_populates="project")
    test_cases: Mapped[List["TestCase"]] = relationship(back_populates="project")


class Requirement(Base):
    """A requirement within a project."""
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("requirements.id"), nullable=True
    )
    req_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    req_type: Mapped[str] = mapped_column(String(30), default="Functional")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped["Project"] = relationship(back_populates="requirements")
    parent: Mapped[Optional["Requirement"]] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Requirement"]] = relationship(back_populates="parent")
    test_case_links: Mapped[List["RequirementTestCase"]] = relationship(back_populates="requirement")
    test_run_links: Mapped[List["TestRunLink"]] = relationship(back_populates="requirement")


class TestCase(Base):
    """A test case that can be linked to requirements."""
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped["Project"] = relationship(back_populates="test_cases")
    requirement_links: Mapped[List["RequirementTestCase"]] = relationship(back_populates="test_case")


class RequirementTestCase(Base):
    """Junction table linking requirements to test cases."""
    __tablename__ = "requirement_test_cases"
    __table_args__ = (
        UniqueConstraint("requirement_id", "test_case_id", name="uq_req_tc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requirement: Mapped["Requirement"] = relationship(back_populates="test_case_links")
    test_case: Mapped["TestCase"] = relationship(back_populates="requirement_links")


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
