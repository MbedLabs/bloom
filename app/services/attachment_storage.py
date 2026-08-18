"""Storing files against a document.

Bytes go to disk under a generated name; the name a person typed is only ever
data. Sizes are enforced while streaming rather than from a declared length, so
a lying Content-Length cannot fill the volume.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import DocumentAttachment

CHUNK_BYTES = 1024 * 1024

_ROOT: Path | None = None


@dataclass
class StoredFile:
    size_bytes: int
    sha256: str


def get_attachment_root() -> Path:
    global _ROOT
    if _ROOT is None:
        _ROOT = Path(settings.ATTACHMENT_DIR).resolve()
    return _ROOT


def ensure_attachment_dir() -> Path:
    root = get_attachment_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_display_name(filename: str | None) -> str:
    """The name shown to a reader, stripped of anything that is a path."""
    candidate = Path(filename or "").name.strip()
    if not candidate or candidate in {".", ".."}:
        raise HTTPException(status_code=422, detail="A file needs a name.")
    if len(candidate) > 255:
        raise HTTPException(status_code=422, detail="That file name is too long.")
    return candidate


def storage_name(display_name: str) -> str:
    """A generated name, keeping only an extension that is plainly alphanumeric."""
    suffix = Path(display_name).suffix
    keep = suffix.lower() if suffix[1:].isalnum() and len(suffix) <= 10 else ""
    return f"{uuid.uuid4()}{keep}"


def require_allowed_type(content_type: str | None) -> str:
    resolved = content_type or "application/octet-stream"
    if resolved not in settings.ALLOWED_ATTACHMENT_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported media type '{resolved}'. Allowed: "
                + ", ".join(settings.ALLOWED_ATTACHMENT_MIME_TYPES)
            ),
        )
    return resolved


def ensure_free_space(remaining_bytes: int) -> None:
    free = shutil.disk_usage(ensure_attachment_dir()).free
    if free < settings.MIN_ATTACHMENT_FREE_BYTES + max(0, remaining_bytes):
        raise HTTPException(
            status_code=507, detail="Not enough free space to accept this file safely."
        )


async def remaining_quota(db: AsyncSession, document_id: int) -> int:
    used = await db.scalar(
        select(func.coalesce(func.sum(DocumentAttachment.size_bytes), 0)).where(
            DocumentAttachment.document_id == document_id
        )
    )
    return max(0, settings.MAX_DOCUMENT_ATTACHMENT_BYTES - int(used or 0))


def resolve_stored_path(storage_path: str) -> Path:
    """Rebuild the full path from the trusted root and reject anything outside it."""
    root = get_attachment_root()
    resolved = (root / storage_path).resolve()
    if resolved.parent != root:
        raise HTTPException(status_code=400, detail="Invalid attachment path.")
    return resolved


async def write_stream(file: UploadFile, final_path: Path, *, max_bytes: int) -> StoredFile:
    """Stream to a temporary file, then move it into place."""
    temp_path = final_path.parent / f".attachment-{uuid.uuid4().hex}.part"
    size = 0
    digest = hashlib.sha256()
    ensure_free_space(max_bytes)

    try:
        with open(temp_path, "xb") as output:
            while chunk := await file.read(CHUNK_BYTES):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. {max_bytes} bytes are available.",
                    )
                digest.update(chunk)
                output.write(chunk)
        os.replace(temp_path, final_path)
    except BaseException:
        for path in (temp_path, final_path):
            with contextlib.suppress(OSError):
                path.unlink()
        raise

    return StoredFile(size_bytes=size, sha256=digest.hexdigest())


def write_bytes(payload: bytes, final_path: Path, *, max_bytes: int) -> StoredFile:
    """Store bytes already in hand, under the same limits as a stream."""
    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"File too large. {max_bytes} bytes are available."
        )
    ensure_free_space(len(payload))
    final_path.write_bytes(payload)
    return StoredFile(size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())


def unlink_quietly(storage_path: str) -> None:
    with contextlib.suppress(OSError, HTTPException):
        resolve_stored_path(storage_path).unlink()
