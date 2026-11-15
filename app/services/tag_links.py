"""Turn the artefact tags written in a document body into references links."""

from __future__ import annotations

import re
from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS
from app.core.link_rules import TAG_ROLE, is_allowed_tag_pair, normalize_linkable_type
from app.core.security import get_external_doc_types, row_allows
from app.models import (
    ArtefactLink,
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
from app.models.user import User

LINK_END_MODELS = {
    "REQ": Requirement,
    "TC": TestCase,
    "DES": DesignItem,
    "RSK": RiskItem,
    "CHG": ChangeRequest,
    "CPT": TestConcept,
    "DEF": Defect,
    "CMP": TestCampaign,
    "TS": TestSuite,
}


async def link_end(
    db: AsyncSession,
    project_id: int,
    end_type: str,
    end_id: int,
    user: User,
) -> tuple[Any, bool]:
    """Load a same-project link endpoint and evaluate view against its complete policy scope."""
    normalized = normalize_linkable_type(end_type)
    if normalized in LINK_END_MODELS:
        model = LINK_END_MODELS[normalized]
        query = select(model).where(model.project_id == project_id, model.id == end_id)
    elif normalized in CANONICAL_DOCUMENT_KINDS:
        query = select(Document).where(
            Document.project_id == project_id,
            Document.id == end_id,
            Document.doc_type == normalized,
        )
    else:
        return None, False
    row = (await db.execute(query)).scalar_one_or_none()
    if row is None:
        return None, False
    return row, await row_allows(db, user, row, "view", normalized)


TAG_TRIGGER = "#"

PUBLIC_ID_COLUMNS = {
    "REQ": "req_id",
    "TC": "tc_id",
    "DES": "design_id",
    "RSK": "risk_id",
    "CHG": "change_id",
    "CPT": "concept_id",
    "DEF": "defect_id",
    "CMP": "campaign_id",
    "TS": "suite_id",
}

TEXT_TAG = re.compile(r"(?<![\w#])#([A-Z][A-Z0-9]*-[A-Z]+-\d+)\b")


async def text_tag_content(
    db: AsyncSession, project_id: int, source_type: str, text: str | None
) -> list[dict]:
    """Tag mention nodes for each #ID in plain text that names an allowed record of the project."""
    source = normalize_linkable_type(source_type)
    nodes: list[dict] = []
    for public_id in dict.fromkeys(TEXT_TAG.findall(text or "")):
        type_code = normalize_linkable_type(public_id.split("-")[-2])
        if not is_allowed_tag_pair(source, type_code):
            continue
        if type_code in PUBLIC_ID_COLUMNS:
            model = LINK_END_MODELS[type_code]
            column = getattr(model, PUBLIC_ID_COLUMNS[type_code])
            query = select(model.id).where(model.project_id == project_id, column == public_id)
        elif type_code in CANONICAL_DOCUMENT_KINDS:
            query = select(Document.id).where(
                Document.project_id == project_id,
                Document.doc_id == public_id,
                Document.doc_type == type_code,
            )
        else:
            continue
        row_id = (await db.execute(query)).scalar_one_or_none()
        if row_id is not None:
            nodes.append(
                {
                    "type": "mention",
                    "attrs": {"id": f"{type_code}:{row_id}", "mentionSuggestionChar": TAG_TRIGGER},
                }
            )
    return nodes


def _walk(node: Any) -> Iterable[dict]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def extract_tags(content_json: Any) -> list[tuple[str, int]]:
    tags: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for node in _walk(content_json):
        if node.get("type") != "mention":
            continue
        attrs = node.get("attrs") or {}
        if attrs.get("mentionSuggestionChar") != TAG_TRIGGER:
            continue
        raw = str(attrs.get("id") or "")
        target_type, _, raw_id = raw.partition(":")
        if not target_type or not raw_id.isdigit():
            continue
        pair = (normalize_linkable_type(target_type), int(raw_id))
        if pair in seen:
            continue
        seen.add(pair)
        tags.append(pair)
    return tags


async def sync_tag_links(
    db: AsyncSession,
    *,
    project_id: int,
    source_type: str,
    source_id: int,
    content_json: Any,
    user: User,
) -> int:
    source = normalize_linkable_type(source_type)
    tags = []
    for target_type, target_id in extract_tags(content_json):
        if target_type == source and target_id == source_id:
            continue
        if not is_allowed_tag_pair(source, target_type):
            raise HTTPException(
                status_code=422,
                detail=f"Tag {target_type}:{target_id}: references from {source} is not allowed",
            )
        tags.append((target_type, target_id))
    if not tags:
        return 0
    await get_external_doc_types(db, user, project_id)
    tags = [
        (target_type, target_id)
        for target_type, target_id in tags
        if (await link_end(db, project_id, target_type, target_id, user))[1]
    ]
    if not tags:
        return 0

    existing = set(
        (
            await db.execute(
                select(ArtefactLink.target_type, ArtefactLink.target_id).where(
                    ArtefactLink.project_id == project_id,
                    ArtefactLink.source_type == source,
                    ArtefactLink.source_id == source_id,
                    ArtefactLink.role == TAG_ROLE,
                )
            )
        ).all()
    )

    created = 0
    for target_type, target_id in tags:
        if (target_type, target_id) in existing:
            continue
        db.add(
            ArtefactLink(
                project_id=project_id,
                source_type=source,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                role=TAG_ROLE,
            )
        )
        created += 1
    return created
