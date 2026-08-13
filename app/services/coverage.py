"""Requirement test coverage - one definition, used everywhere.

Coverage used to be computed in three places with two incompatible rules:
``projects.py`` and ``dashboard.py`` counted a requirement as covered as soon
as any test case verified it, while ``traceability.py`` refused to count a
requirement whose verifying test cases were all still ``Draft``. The same
project therefore reported a higher percentage on its card and on the
dashboard than on the traceability page that exists to report exactly that
number.

The traceability rule is the correct one - a draft test case has not verified
anything yet - so it is the rule implemented here, once, in both a Python and
a SQL form that are deliberately kept equivalent.
"""

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
    """Select the ids of requirements verified by at least one non-draft test case.

    ``Requirement`` and ``TestCase`` are both joined so callers can add their
    own project scoping and external-visibility filters to either side. The
    ``TestCase.status`` predicate is the SQL twin of :func:`verifies`;
    ``is_distinct_from`` rather than ``!=`` so a null status would be treated
    the same way Python treats it.
    """
    return (
        select(ArtefactLink.target_id)
        .join(TestCase, TestCase.id == ArtefactLink.source_id)
        .join(Requirement, Requirement.id == ArtefactLink.target_id)
        .where(
            ArtefactLink.source_type == VERIFY_SOURCE_TYPE,
            ArtefactLink.target_type == VERIFY_TARGET_TYPE,
            ArtefactLink.role == VERIFY_LINK_ROLE,
            TestCase.status.is_distinct_from(DRAFT_STATUS),
        )
    )


def coverage_percent(covered: int, total: int) -> float:
    """Percentage of requirements covered, to one decimal place."""
    return round((covered / total * 100) if total else 0, 1)
