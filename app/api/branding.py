"""Instance report branding: an admin-uploaded company logo shown in PDF reports."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models import ReportBranding
from app.models.user import User, UserRole

router = APIRouter()

ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_LOGO_BYTES = 2_000_000


async def _branding_row(db: AsyncSession) -> ReportBranding:
    row = (await db.execute(select(ReportBranding).limit(1))).scalar_one_or_none()
    if row is None:
        row = ReportBranding()
        db.add(row)
        await db.flush()
    return row


@router.put("/logo")
async def set_report_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Store the company logo used in PDF reports (admin only)."""
    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=415, detail="Logo must be a PNG, JPEG, GIF or WebP image")
    raw = await file.read()
    if len(raw) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=413, detail="Logo image too large (max 2 MB)")
    branding = await _branding_row(db)
    branding.logo = raw
    branding.logo_content_type = file.content_type
    branding.logo_filename = file.filename
    await db.flush()
    return {"content_type": file.content_type, "size": len(raw)}


@router.get("/logo")
async def get_report_logo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the stored company logo, or 404 when none is set."""
    row = (await db.execute(select(ReportBranding).limit(1))).scalar_one_or_none()
    if row is None or not row.logo:
        raise HTTPException(status_code=404, detail="No report logo set")
    return Response(content=row.logo, media_type=row.logo_content_type or "image/png")


@router.delete("/logo", status_code=204)
async def delete_report_logo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Remove the stored company logo (admin only)."""
    row = (await db.execute(select(ReportBranding).limit(1))).scalar_one_or_none()
    if row is not None:
        row.logo = None
        row.logo_content_type = None
        row.logo_filename = None
        await db.flush()
