"""Registry describing which artefact models global search covers and how."""

from dataclasses import dataclass
from typing import Optional

from app.models import (
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


@dataclass(frozen=True)
class SearchTarget:
    """One searchable artefact type.

    type_code is the canonical code shown to the client, id_attr the human-readable id column,
    title_attr the display title column, and doc_type_attr is set for documents, which carry their
    own doc_type.
    """

    type_code: str
    model: type
    id_attr: str
    title_attr: str
    doc_type_attr: Optional[str] = None


SEARCH_TARGETS: tuple[SearchTarget, ...] = (
    SearchTarget("REQ", Requirement, "req_id", "title"),
    SearchTarget("TC", TestCase, "tc_id", "title"),
    SearchTarget("DOC", Document, "doc_id", "title", doc_type_attr="doc_type"),
    SearchTarget("DES", DesignItem, "design_id", "title"),
    SearchTarget("RSK", RiskItem, "risk_id", "title"),
    SearchTarget("CHG", ChangeRequest, "change_id", "title"),
    SearchTarget("CPT", TestConcept, "concept_id", "name"),
    SearchTarget("DEF", Defect, "defect_id", "title"),
    SearchTarget("TS", TestSuite, "suite_id", "name"),
    SearchTarget("CMP", TestCampaign, "campaign_id", "name"),
)


def rank_match(query_lower: str, doc_id: Optional[str], title: Optional[str]) -> int:
    """Rank a candidate row for ordering: lower is better."""
    did = (doc_id or "").lower()
    ttl = (title or "").lower()
    if did == query_lower:
        return 0
    if did.startswith(query_lower):
        return 1
    if ttl.startswith(query_lower):
        return 2
    if query_lower in did:
        return 3
    if query_lower in ttl:
        return 4
    return 5
