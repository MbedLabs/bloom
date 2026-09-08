"""Turn the artefact tags written in a document body into references links."""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.link_rules import TAG_ROLE, is_allowed_tag_pair, normalize_linkable_type
from app.models import ArtefactLink

TAG_TRIGGER = "#"


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
) -> int:
    source = normalize_linkable_type(source_type)
    tags = [
        (target_type, target_id)
        for target_type, target_id in extract_tags(content_json)
        if is_allowed_tag_pair(source, target_type)
        and not (target_type == source and target_id == source_id)
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
