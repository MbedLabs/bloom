"""Admin lifecycle endpoints for scoped machine credentials."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_role
from app.core.service_auth import (
    SERVICE_SCOPE,
    create_service_credential,
    revoke_service_credential,
)
from app.models import ServiceCredential
from app.models.user import User, UserRole

router = APIRouter()


class ServiceCredentialCreate(BaseModel):
    name: str = Field(default="Bud result sync", min_length=1, max_length=100)
    scope: str = SERVICE_SCOPE
    expires_in_days: int = Field(default=90, ge=1, le=90)


class ServiceCredentialSummary(BaseModel):
    id: int
    name: str
    token_prefix: str
    scope: str
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceCredentialCreated(ServiceCredentialSummary):
    token: str


def _validate_scope(scope: str) -> None:
    if scope != SERVICE_SCOPE:
        raise HTTPException(
            status_code=422,
            detail=f"Only the exact '{SERVICE_SCOPE}' scope is supported.",
        )


@router.get("", response_model=list[ServiceCredentialSummary])
async def list_service_credentials(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.admin)),
):
    return list(
        (
            await db.scalars(
                select(ServiceCredential).order_by(ServiceCredential.created_at.desc())
            )
        ).all()
    )


@router.post("", response_model=ServiceCredentialCreated, status_code=201)
async def create_credential(
    data: ServiceCredentialCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    _validate_scope(data.scope)
    credential, token = await create_service_credential(
        db,
        created_by_user_id=admin.id,
        name=data.name,
        expires_in_days=data.expires_in_days,
    )
    summary = ServiceCredentialSummary.model_validate(credential)
    return ServiceCredentialCreated(
        **summary.model_dump(),
        token=token,
    )


@router.post("/{credential_id}/rotate", response_model=ServiceCredentialCreated)
async def rotate_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    existing = await db.get(ServiceCredential, credential_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Service credential not found.")
    name = existing.name
    await revoke_service_credential(db, credential_id)
    credential, token = await create_service_credential(db, created_by_user_id=admin.id, name=name)
    summary = ServiceCredentialSummary.model_validate(credential)
    return ServiceCredentialCreated(
        **summary.model_dump(),
        token=token,
    )


@router.delete("/{credential_id}", status_code=204)
async def revoke_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(UserRole.admin)),
):
    await revoke_service_credential(db, credential_id)
