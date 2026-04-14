"""
FastAPI application for EmbedLabs Bloom - Application Lifecycle Management.

Main entry point for the backend API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import health, projects, requirements, test_cases, traceability
from app.core.config import settings
from app.core.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    await create_tables()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["Requirements"])
app.include_router(test_cases.router, prefix="/api/test-cases", tags=["Test Cases"])
app.include_router(traceability.router, prefix="/api/traceability", tags=["Traceability"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": settings.BLOOM_APP_NAME,
        "version": settings.BLOOM_APP_VERSION,
    }
