"""
FastAPI application for EmbedLabs Bloom - Application Lifecycle Management.

Main entry point for the backend API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.api import health, projects, requirements, test_cases, traceability, documents, campaigns, dashboard, designs, risks, changes, baselines, test_concepts, artefacts, test_suites, links, project_variables, import_service, docs_facade
from app.api import auth as auth_api
from app.api import users as users_api
from app.core.config import settings
from app.core.deps import limiter
from app.core.database import create_tables, async_session_maker
from app.core.security import get_password_hash
from app.models.user import User, UserRole


async def seed_admin_user():
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.ADMIN_EMAIL,
                full_name=settings.ADMIN_FULL_NAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.admin,
                is_active=True,
            )
            session.add(admin)
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    await create_tables()
    await seed_admin_user()
    yield


app = FastAPI(
    title=settings.BLOOM_APP_NAME,
    description="Backend API for EmbedLabs Bloom - Application Lifecycle Management",
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
app.include_router(project_variables.router, prefix="/api/project-variables", tags=["Project Variables"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["Requirements"])
app.include_router(test_cases.router, prefix="/api/test-cases", tags=["Test Cases"])
app.include_router(traceability.router, prefix="/api/traceability", tags=["Traceability"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(test_suites.router, prefix="/api/test-suites", tags=["Test Suites"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(designs.router, prefix="/api/designs", tags=["Designs"])
app.include_router(risks.router, prefix="/api/risks", tags=["Risks"])
app.include_router(changes.router, prefix="/api/changes", tags=["Changes"])
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
