"""Requirement test coverage - one definition, used everywhere."""

from typing import Iterable, Optional

from sqlalchemy import Select, select

from app.models import ArtefactLink, Requirement, TestCase

DRAFT_STATUS = "Draft"

COVERED = "Covered"
PARTIAL = "Partial"
UNCOVERED = "Uncovered"

VERIFY_SOURCE_TYPE = "TC"
VERIFY_TARGET_TYPE = "REQ"
VERIFY_LINK_ROLE = "verifies"


def verifies(test_case_status: Optional[str]) -> bool:
    """Whether a test case in this status actually verifies its requirement."""
    return test_case_status != DRAFT_STATUS


def coverage_status(test_case_statuses: Iterable[Optional[str]]) -> str:
    """Classify a requirement from the statuses of the test cases verifying it."""
    statuses = list(test_case_statuses)
    if not statuses:
        return UNCOVERED
    if any(verifies(status) for status in statuses):
        return COVERED
    return PARTIAL


def covered_requirement_ids() -> Select:
    """Select requirement ids with at least one verifying test case."""
    return (
        select(ArtefactLink.target_id)
        .join(TestCase, TestCase.id == ArtefactLink.source_id)
        .join(Requirement, Requirement.id == ArtefactLink.target_id)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            ArtefactLink.role == VERIFY_LINK_ROLE,
        )
    )


def coverage_percent(covered: int, total: int) -> float:
    """Percentage of requirements covered, to one decimal place."""
    return round((covered / total * 100) if total else 0, 1)
