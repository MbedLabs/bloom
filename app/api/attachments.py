"""Files held against a document.

Access follows the document: whoever may read it may read what is attached to
it, and only a maintainer may add or remove. Downloads are always served as an
attachment, never inline, so a stored SVG or HTML cannot execute in the
browsing user's session.
"""

from __future__ import annotations

import base64
import binascii
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.docs_facade import resolve_project
from app.core.config import settings
from app.core.database import get_db
from app.core.id_generator import next_doc_id
from app.core.security import get_current_user, require_project_access, require_role
from app.core.service_auth import require_bud_sync_token
from app.models import Document, DocumentAttachment
from app.models.user import User, UserRole
from app.schemas import (
    DocumentAttachmentResponse,
    TestReportFile,
    TestReportPublish,
    TestReportPublishResponse,
)
from app.services import attachment_storage as storage
from app.services.attachment_upload_policy import (
    release_attachment_upload,
    reserve_attachment_upload,
)

router = APIRouter()


async def _readable_document(db: AsyncSession, document_id: int, user: User) -> Document:
    document = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_project_access(db, user, document.project_id)
    return document


async def _writable_document(db: AsyncSession, document_id: int, user: User) -> Document:
    document = (
        await db.execute(select(Document).where(Document.id == document_id))
    ).scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_project_access(
        db,
        user,
        document.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )
    return document


@router.get("/documents/{document_id}/attachments", response_model=list[DocumentAttachmentResponse])
async def list_attachments(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Everything held against this document, oldest first."""
    await _readable_document(db, document_id, current_user)
    rows = (
        await db.execute(
            select(DocumentAttachment)
            .where(DocumentAttachment.document_id == document_id)
            .order_by(DocumentAttachment.created_at, DocumentAttachment.id)
        )
    ).scalars()
    return rows.all()


@router.post(
    "/documents/{document_id}/attachments",
    response_model=DocumentAttachmentResponse,
    status_code=201,
)
async def upload_attachment(
    document_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Attach a file to a document."""
    document = await _writable_document(db, document_id, current_user)
    display_name = storage.safe_display_name(file.filename)
    content_type = storage.require_allowed_type(file.content_type)

    remaining = await storage.remaining_quota(db, document.id)
    if remaining <= 0:
        raise HTTPException(status_code=413, detail="This document has no attachment space left.")
    budget = min(remaining, settings.MAX_ATTACHMENT_SIZE)

    lease = await reserve_attachment_upload(db, user_id=current_user.id)
    try:
        root = storage.ensure_attachment_dir()
        stored_name = storage.storage_name(display_name)
        written = await storage.write_stream(file, root / stored_name, max_bytes=budget)

        attachment = DocumentAttachment(
            document_id=document.id,
            filename=stored_name,
            original_filename=display_name,
            content_type=content_type,
            size_bytes=written.size_bytes,
            sha256=written.sha256,
            storage_path=stored_name,
            uploaded_by_id=current_user.id,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment
    except BaseException:
        await db.rollback()
        raise
    finally:
        await release_attachment_upload(db, lease.id)


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download one attachment."""
    attachment = (
        await db.execute(
            select(DocumentAttachment)
            .options(selectinload(DocumentAttachment.document))
            .where(DocumentAttachment.id == attachment_id)
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await require_project_access(db, current_user, attachment.document.project_id)

    path = storage.resolve_stored_path(attachment.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    name = attachment.original_filename
    return FileResponse(
        path=str(path),
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{name}\"; filename*=UTF-8''{quote(name)}"
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.maintainer)),
):
    """Remove an attachment and the file behind it."""
    attachment = (
        await db.execute(
            select(DocumentAttachment)
            .options(selectinload(DocumentAttachment.document))
            .where(DocumentAttachment.id == attachment_id)
        )
    ).scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await require_project_access(
        db,
        current_user,
        attachment.document.project_id,
        roles={UserRole.admin.value, UserRole.maintainer.value},
    )

    storage_path = attachment.storage_path
    await db.delete(attachment)
    await db.commit()
    storage.unlink_quietly(storage_path)
    return Response(status_code=204)


@router.post(
    "/bud/test-reports",
    response_model=TestReportPublishResponse,
    status_code=201,
)
async def publish_test_report(
    data: TestReportPublish,
    db: AsyncSession = Depends(get_db),
    _service_credential=Depends(require_bud_sync_token),
):
    """Receive a Bud run's report as a Report (RPT) document.

    Publishing is a decision made in Bud, not a consequence of running tests:
    a suite that runs nightly would otherwise mint a Report a night. Re-sending
    the same run updates the document it already made rather than adding
    another, so a retry is safe and a re-publish is a correction.
    """
    project = await resolve_project(db, data.project_prefix)
    source_ref = f"bud-run:{data.bud_run_id}"

    document = (
        await db.execute(
            select(Document).where(
                Document.project_id == project.id,
                Document.doc_type == "RPT",
                Document.source_ref == source_ref,
            )
        )
    ).scalar_one_or_none()

    created = document is None
    if created:
        document = Document(
            project_id=project.id,
            doc_id=await next_doc_id(
                db, Document, Document.doc_id, project.id, project.prefix, "RPT"
            ),
            title=f"{data.run_name} - Bud run {data.bud_run_id}",
            doc_type="RPT",
            status="Draft",
            source_ref=source_ref,
        )
        db.add(document)
        await db.flush()

    document.title = f"{data.run_name} - Bud run {data.bud_run_id}"
    document.description = _report_summary(data)
    await db.flush()

    attachment_ids: list[int] = []
    for item in data.files:
        attachment_ids.append(await _replace_report_file(db, document, item, source_ref))

    await db.commit()
    await db.refresh(document)
    return TestReportPublishResponse(
        document_id=document.id,
        doc_id=document.doc_id,
        created=created,
        attachment_ids=attachment_ids,
    )


def _report_summary(data: TestReportPublish) -> str:
    executed = data.executed_at.isoformat() if data.executed_at else "unknown"
    lines = [
        f"Bud run {data.bud_run_id} ({data.status or 'Completed'}) executed {executed}.",
        f"{data.passed_tests} passed, {data.failed_tests} failed, of {data.total_tests}.",
    ]
    if data.tc_ids:
        lines.append("Test cases: " + ", ".join(sorted(set(data.tc_ids))))
    if data.run_url:
        lines.append(f"Run in Bud: {data.run_url}")
    return "\n".join(lines)


async def _replace_report_file(
    db: AsyncSession, document: Document, item: TestReportFile, source_ref: str
) -> int:
    """Store one published file, replacing the previous delivery of the same name."""
    display_name = storage.safe_display_name(item.filename)
    content_type = storage.require_allowed_type(item.content_type)
    try:
        payload = base64.b64decode(item.content_base64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=422, detail=f"'{display_name}' is not valid base64"
        ) from exc

    previous = (
        await db.execute(
            select(DocumentAttachment).where(
                DocumentAttachment.document_id == document.id,
                DocumentAttachment.source_ref == source_ref,
                DocumentAttachment.original_filename == display_name,
            )
        )
    ).scalar_one_or_none()

    remaining = await storage.remaining_quota(db, document.id)
    if previous is not None:
        remaining += previous.size_bytes
    budget = min(max(remaining, 0), settings.MAX_ATTACHMENT_SIZE)
    if budget <= 0:
        raise HTTPException(status_code=413, detail="This document has no attachment space left.")

    root = storage.ensure_attachment_dir()
    stored_name = storage.storage_name(display_name)
    written = storage.write_bytes(payload, root / stored_name, max_bytes=budget)

    if previous is not None:
        stale = previous.storage_path
        await db.delete(previous)
        await db.flush()
        storage.unlink_quietly(stale)

    attachment = DocumentAttachment(
        document_id=document.id,
        filename=stored_name,
        original_filename=display_name,
        content_type=content_type,
        size_bytes=written.size_bytes,
        sha256=written.sha256,
        storage_path=stored_name,
        source_ref=source_ref,
    )
    db.add(attachment)
    await db.flush()
    return attachment.id
