"""Streamed attachment limits, checksums and cleanup on interrupted reads."""

import asyncio
import hashlib
import io

import pytest
from fastapi import HTTPException, UploadFile

from app.services import attachment_storage


@pytest.fixture
def stream_path(monkeypatch, tmp_path):
    monkeypatch.setattr(attachment_storage, "get_attachment_root", lambda: tmp_path)
    monkeypatch.setattr(attachment_storage, "CHUNK_BYTES", 3)
    return tmp_path / "attachment.txt"


async def test_stream_preserves_content_size_and_checksum(stream_path):
    payload = b"streamed attachment"
    upload = UploadFile(file=io.BytesIO(payload))
    stored = await attachment_storage.write_stream(upload, stream_path, max_bytes=len(payload))
    assert stream_path.read_bytes() == payload
    assert stored.size_bytes == len(payload)
    assert stored.sha256 == hashlib.sha256(payload).hexdigest()
    assert list(stream_path.parent.glob("*.part")) == []


async def test_oversize_stream_removes_partial_files(stream_path):
    upload = UploadFile(file=io.BytesIO(b"too many bytes"))
    with pytest.raises(HTTPException) as failure:
        await attachment_storage.write_stream(upload, stream_path, max_bytes=4)
    assert failure.value.status_code == 413
    assert not stream_path.exists()
    assert list(stream_path.parent.iterdir()) == []


@pytest.mark.parametrize("error", [OSError, asyncio.CancelledError])
async def test_interrupted_stream_removes_partial_files(stream_path, error):
    class InterruptedUpload:
        """Yield one chunk before the read is interrupted."""

        def __init__(self):
            self.reads = 0

        async def read(self, size):
            self.reads += 1
            if self.reads > 1:
                raise error()
            return b"one"

    upload = InterruptedUpload()
    with pytest.raises(error):
        await attachment_storage.write_stream(upload, stream_path, max_bytes=8)
    assert upload.reads == 2
    assert list(stream_path.parent.iterdir()) == []
