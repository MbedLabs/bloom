"""Resource limits for untrusted ReqIF and ReqIFZ input."""

from __future__ import annotations

import io
import zipfile
from typing import Protocol

from app.core.config import settings


class ReqIFParseError(ValueError):
    """Raised when supplied bytes violate the ReqIF input policy or syntax."""


class AsyncUpload(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


async def read_reqif_upload(upload: AsyncUpload) -> bytes:
    """Read a request incrementally and stop immediately beyond the 25 MiB cap."""

    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(settings.REQIF_STREAM_CHUNK_BYTES):
        total += len(chunk)
        if total > settings.REQIF_MAX_REQUEST_BYTES:
            raise ReqIFParseError("ReqIF request exceeds the 25 MiB streamed request limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_member(info: zipfile.ZipInfo) -> None:
    if info.flag_bits & 0x1:
        raise ReqIFParseError("Encrypted ReqIF archive entries are not accepted.")
    if info.is_dir():
        raise ReqIFParseError("The ReqIF archive member must be a regular file.")
    if info.file_size > settings.REQIF_MAX_MEMBER_BYTES:
        raise ReqIFParseError("ReqIF uncompressed member exceeds the 25 MiB limit.")
    if info.file_size and info.compress_size == 0:
        raise ReqIFParseError("ReqIF archive has an invalid compression ratio.")
    if info.compress_size and (
        info.file_size / info.compress_size > settings.REQIF_MAX_COMPRESSION_RATIO
    ):
        raise ReqIFParseError("ReqIF archive exceeds the maximum 20:1 compression ratio.")


def extract_reqif_xml(data: bytes) -> bytes:
    """Return bounded XML bytes, strictly validating a ReqIFZ container first."""

    if data[:2] != b"PK":
        if len(data) > settings.REQIF_MAX_MEMBER_BYTES:
            raise ReqIFParseError("ReqIF uncompressed member exceeds the 25 MiB limit.")
        return data

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > settings.REQIF_MAX_ARCHIVE_ENTRIES:
                raise ReqIFParseError("ReqIF archive exceeds the maximum archive entries.")
            members = [
                info
                for info in entries
                if not info.is_dir() and info.filename.lower().endswith(".reqif")
            ]
            if len(members) != 1:
                raise ReqIFParseError("ReqIF archive must contain exactly one .reqif member.")
            member = members[0]
            _validate_member(member)
            output = io.BytesIO()
            actual_size = 0
            with archive.open(member, "r") as source:
                while chunk := source.read(settings.REQIF_STREAM_CHUNK_BYTES):
                    actual_size += len(chunk)
                    if actual_size > settings.REQIF_MAX_MEMBER_BYTES:
                        raise ReqIFParseError("ReqIF uncompressed member exceeds the 25 MiB limit.")
                    output.write(chunk)
            if actual_size != member.file_size:
                raise ReqIFParseError("ReqIF archive member size metadata is inconsistent.")
            return output.getvalue()
    except zipfile.BadZipFile as exc:
        raise ReqIFParseError("Corrupt ReqIF archive.") from exc
