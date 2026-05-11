"""
FastAPI application for EmbedLabs Bloom - Product Lifecycle Management.

Main entry point for the backend API.
"""

import logging
import re
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import or_, select, text

from app.api import artefacts
from app.api import auth as auth_api
from app.api import (
    baselines,
    campaigns,
    changes,
    dashboard,
    defects,
    designs,
    docs_facade,
    documents,
    health,
    import_service,
    integrations,
    links,
    project_variables,
    projects,
    requirements,
    risks,
    test_cases,
    test_concepts,
    test_suites,
    traceability,
)
from app.api import users as users_api
from app.core.config import settings
from app.core.database import async_session_maker, create_tables, engine
from app.core.deps import limiter
from app.core.document_kinds import CANONICAL_DOCUMENT_KINDS, normalize_document_kind
from app.core.id_generator import compute_next_id, next_doc_id
from app.core.security import get_password_hash
from app.models import ArtefactLink, Document, Project, TestCampaign
from app.models.user import User, UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


async def seed_admin_user():
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                email=settings.ADMIN_EMAIL,
                full_name=settings.ADMIN_FULL_NAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.admin,
                is_active=True,
            )
            session.add(admin)
        else:
            admin.role = UserRole.admin
            admin.is_active = True

        await session.commit()


async def migrate_user_columns() -> None:
    """Ensure newer user columns exist on legacy databases."""
    if engine.dialect.name != "postgresql":
        return

    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_token_jti VARCHAR(255) NULL")
        )


async def normalize_document_kinds_and_ids() -> None:
    """Normalize legacy shared-document types and ids to canonical kind codes."""
    async with async_session_maker() as session:
        projects = (await session.execute(select(Project).order_by(Project.id))).scalars().all()
        id_pattern = re.compile(r"^(?P<prefix>[A-Z0-9]+)-(?P<kind>[A-Z]+)-(?P<num>\d+)$")

        for project in projects:
            documents = (
                (
                    await session.execute(
                        select(Document)
                        .where(Document.project_id == project.id)
                        .order_by(Document.created_at.asc(), Document.id.asc())
                    )
                )
                .scalars()
                .all()
            )

            used_ids_by_kind: dict[str, set[str]] = {
                kind: set() for kind in CANONICAL_DOCUMENT_KINDS
            }
            for document in documents:
                normalized_kind = normalize_document_kind(document.doc_type)
                if normalized_kind not in CANONICAL_DOCUMENT_KINDS:
                    normalized_kind = "SPEC"

                current_id = document.doc_id or ""
                if current_id.startswith(f"{project.prefix}-{normalized_kind}-"):
                    used_ids_by_kind[normalized_kind].add(current_id)

            for document in documents:
                normalized_kind = normalize_document_kind(document.doc_type)
                if normalized_kind not in CANONICAL_DOCUMENT_KINDS:
                    normalized_kind = "SPEC"
                document.doc_type = normalized_kind

                current_id = document.doc_id or ""
                desired_prefix = f"{project.prefix}-{normalized_kind}-"
                if current_id.startswith(desired_prefix):
                    continue

                replacement_id = None
                match = id_pattern.match(current_id)
                if match and match.group("prefix") == project.prefix:
                    candidate = f"{desired_prefix}{match.group('num')}"
                    if candidate not in used_ids_by_kind[normalized_kind]:
                        replacement_id = candidate

                if replacement_id is None:
                    existing_ids = sorted(used_ids_by_kind[normalized_kind])
                    replacement_id = compute_next_id(existing_ids, project.prefix, normalized_kind)

                document.doc_id = replacement_id
                used_ids_by_kind[normalized_kind].add(replacement_id)

            documents_by_id = {document.id: document for document in documents}
            links = (
                (
                    await session.execute(
                        select(ArtefactLink)
                        .where(ArtefactLink.project_id == project.id)
                        .order_by(ArtefactLink.id.asc())
                    )
                )
                .scalars()
                .all()
            )
            seen_link_keys: set[tuple[str, int, str, int, str]] = set()

            for link in links:
                if (
                    link.source_id in documents_by_id
                    and normalize_document_kind(link.source_type) in CANONICAL_DOCUMENT_KINDS
                ):
                    link.source_type = documents_by_id[link.source_id].doc_type
                if (
                    link.target_id in documents_by_id
                    and normalize_document_kind(link.target_type) in CANONICAL_DOCUMENT_KINDS
                ):
                    link.target_type = documents_by_id[link.target_id].doc_type

                link_key = (
                    link.source_type,
                    link.source_id,
                    link.target_type,
                    link.target_id,
                    link.role,
                )
                if link_key in seen_link_keys:
                    await session.delete(link)
                else:
                    seen_link_keys.add(link_key)

        await session.commit()


async def backfill_campaign_public_ids() -> None:
    """Assign PRJ-CMP-NNN to campaigns missing campaign_id (legacy rows)."""
    async with async_session_maker() as session:
        projects = (await session.execute(select(Project).order_by(Project.id))).scalars().all()
        for project in projects:
            campaigns = (
                (
                    await session.execute(
                        select(TestCampaign)
                        .where(
                            TestCampaign.project_id == project.id,
                            or_(
                                TestCampaign.campaign_id.is_(None),
                                TestCampaign.campaign_id == "",
                            ),
                        )
                        .order_by(TestCampaign.id.asc())
                    )
                )
                .scalars()
                .all()
            )
            for campaign in campaigns:
                campaign.campaign_id = await next_doc_id(
                    session,
                    TestCampaign,
                    TestCampaign.campaign_id,
                    project.id,
                    project.prefix,
                    "CMP",
                )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    await create_tables()
    await migrate_user_columns()
    await normalize_document_kinds_and_ids()
    await backfill_campaign_public_ids()
    await seed_admin_user()
    yield


app = FastAPI(
    title=settings.BLOOM_APP_NAME,
    description="Backend API for EmbedLabs Bloom - Product Lifecycle Management",
    version=settings.BLOOM_APP_VERSION,
    docs_url="/api/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/api/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/api/openapi.json" if settings.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# H2: Attach rate-limiter state and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth_api.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users_api.router, prefix="/api/users", tags=["Users"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(
    project_variables.router,
    prefix="/api/project-variables",
    tags=["Project Variables"],
)
app.include_router(requirements.router, prefix="/api/requirements", tags=["Requirements"])
app.include_router(test_cases.router, prefix="/api/test-cases", tags=["Test Cases"])
app.include_router(traceability.router, prefix="/api/traceability", tags=["Traceability"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(test_suites.router, prefix="/api/test-suites", tags=["Test Suites"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(designs.router, prefix="/api/designs", tags=["Designs"])
app.include_router(risks.router, prefix="/api/risks", tags=["Risks"])
app.include_router(changes.router, prefix="/api/changes", tags=["Changes"])
app.include_router(defects.router, prefix="/api/defects", tags=["Defects"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(baselines.router, prefix="/api/baselines", tags=["Baselines"])
app.include_router(test_concepts.router, prefix="/api/test-concepts", tags=["Test Concepts"])
app.include_router(artefacts.router, prefix="/api/artefacts", tags=["Artefacts"])
app.include_router(links.router, prefix="/api/links", tags=["Links"])
app.include_router(import_service.router, prefix="/api", tags=["Import"])
app.include_router(docs_facade.router, prefix="/api", tags=["Docs Facade"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": settings.BLOOM_APP_NAME,
        "version": settings.BLOOM_APP_VERSION,
    }
