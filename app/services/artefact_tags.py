"""The tags given to an artefact when it is created (R-t)."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import transition_action
from app.core.security import creation_allowed, tag_scope
from app.models.tags import ArtefactTag, Tag
from app.models.user import User


async def creation_tags(db: AsyncSession, user: User, project_id: int, tag_ids) -> list[int]:
    """The further tags a new artefact of the project gets from the request: unknown tags
    answer 400, tags none of the user's policies on the project tick 403."""
    wanted = sorted(set(tag_ids))
    if not wanted:
        return wanted
    known = set((await db.execute(select(Tag.id).where(Tag.id.in_(wanted)))).scalars().all())
    if set(wanted) - known:
        raise HTTPException(status_code=400, detail=f"Unknown tags: {sorted(set(wanted) - known)}")
    scope = await tag_scope(db, user, project_id)
    if scope is not None and set(wanted) - scope:
        raise HTTPException(status_code=403, detail="Only tags your policies tick can be given.")
    return wanted


async def attach_tags(db: AsyncSession, tag_type: str, row, tag_ids, user: User) -> None:
    """Authorize the complete new row and record its tags in the same transaction."""
    if not await creation_allowed(db, user, row, tag_ids):
        raise HTTPException(status_code=403, detail="No create policy covers this artefact.")
    if transition_action(
        "", getattr(row, "status", "")
    ) == "approve" and not await creation_allowed(db, user, row, tag_ids, "approve"):
        raise HTTPException(status_code=403, detail="No approve policy covers this artefact.")
    for tag_id in tag_ids:
        db.add(
            ArtefactTag(
                tag_id=tag_id, artefact_type=tag_type, artefact_id=row.id, project_id=row.project_id
            )
        )
    if tag_ids:
        await db.flush()
