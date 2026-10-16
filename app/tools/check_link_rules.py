"""Report invalid typed links and legacy requirement relations, or validate the link constraint."""

import argparse
import asyncio
import json
from collections.abc import Callable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.link_read_utils import LEGACY_REQ_LINK_TYPE_TO_ROLE
from app.core.database import async_session_maker
from app.core.link_rules import allowed_link_triples
from app.models import ArtefactLink, RequirementLink


async def check_link_rules(
    db: AsyncSession, *, validate: bool = False, emit: Callable[[str], None] = print
) -> int:
    """Report invalid current triples and all legacy rows, validating only without invalid triples."""
    allowed = set(allowed_link_triples())
    invalid_count = 0
    for link in (await db.execute(select(ArtefactLink).order_by(ArtefactLink.id))).scalars():
        if (link.source_type, link.target_type, link.role) in allowed:
            continue
        invalid_count += 1
        emit(
            json.dumps(
                {
                    "table": "artefact_links",
                    "id": link.id,
                    "project_id": link.project_id,
                    "source_type": link.source_type,
                    "source_id": link.source_id,
                    "target_type": link.target_type,
                    "target_id": link.target_id,
                    "role": link.role,
                },
                sort_keys=True,
            )
        )
    for link in (await db.execute(select(RequirementLink).order_by(RequirementLink.id))).scalars():
        mapped_role = LEGACY_REQ_LINK_TYPE_TO_ROLE.get(link.link_type)
        emit(
            json.dumps(
                {
                    "table": "requirement_links",
                    "id": link.id,
                    "source_id": link.source_id,
                    "target_id": link.target_id,
                    "link_type": link.link_type,
                    "mapped_role": mapped_role,
                    "allowed": ("REQ", "REQ", mapped_role) in allowed,
                },
                sort_keys=True,
            )
        )
    if invalid_count:
        return 1
    if validate:
        await db.execute(
            text("ALTER TABLE artefact_links VALIDATE CONSTRAINT fk_artefact_links_allowed_triple")
        )
    return 0


async def _run(validate: bool) -> int:
    """Run the link report and commit only a requested constraint validation."""
    async with async_session_maker() as db:
        status = await check_link_rules(db, validate=validate)
        if validate and status == 0:
            await db.commit()
        return status


def main() -> int:
    """Parse command arguments and return the link report status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="validate the constraint when no invalid current triples remain",
    )
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.validate))


if __name__ == "__main__":
    raise SystemExit(main())
