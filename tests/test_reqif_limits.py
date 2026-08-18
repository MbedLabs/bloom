"""Adversarial request and ReqIFZ policy tests."""

import io
import zipfile

import pytest

from app.core.config import settings
from app.core.reqif import ReqIFParseError, parse_reqif
from app.core.reqif_policy import _validate_member, read_reqif_upload
from app.services.reqif_worker import ReqIFProcessingTimeout, parse_reqif_in_worker

MINIMAL_REQIF = (
    b'<REQ-IF xmlns="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
    b"<CORE-CONTENT><REQ-IF-CONTENT><SPEC-OBJECTS>"
    b'<SPEC-OBJECT IDENTIFIER="OBJ-1"><VALUES/></SPEC-OBJECT>'
    b"</SPEC-OBJECTS></REQ-IF-CONTENT></CORE-CONTENT></REQ-IF>"
)


class ChunkedUpload:
    def __init__(self, payload: bytes, max_chunk: int = 3):
        self.payload = payload
        self.offset = 0
        self.max_chunk = max_chunk
        self.read_calls = 0

    async def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if self.offset >= len(self.payload):
            return b""
        requested = len(self.payload) if size < 0 else size
        amount = min(requested, self.max_chunk)
        chunk = self.payload[self.offset : self.offset + amount]
        self.offset += len(chunk)
        return chunk


@pytest.mark.asyncio
async def test_request_at_stream_limit_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_REQUEST_BYTES", 10)
    monkeypatch.setattr(settings, "REQIF_STREAM_CHUNK_BYTES", 4)
    upload = ChunkedUpload(b"x" * 10)

    assert await read_reqif_upload(upload) == b"x" * 10
    assert upload.read_calls > 1


@pytest.mark.asyncio
async def test_request_one_byte_over_stream_limit_stops_early(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_REQUEST_BYTES", 10)
    monkeypatch.setattr(settings, "REQIF_STREAM_CHUNK_BYTES", 4)
    upload = ChunkedUpload(b"x" * 100)

    with pytest.raises(ReqIFParseError, match="request.*25 MiB"):
        await read_reqif_upload(upload)

    assert upload.offset < len(upload.payload)


def _archive(entries: list[tuple[str, bytes]], compression=zipfile.ZIP_STORED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        for name, payload in entries:
            archive.writestr(name, payload)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "entries,error",
    [
        ([("readme.txt", b"no")], "exactly one"),
        ([("a.reqif", MINIMAL_REQIF), ("b.REQIF", MINIMAL_REQIF)], "exactly one"),
        ([("only.xml", MINIMAL_REQIF)], "exactly one"),
    ],
)
def test_archive_requires_exactly_one_reqif_member(entries, error):
    with pytest.raises(ReqIFParseError, match=error):
        parse_reqif(_archive(entries))


def test_archive_entry_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_ARCHIVE_ENTRIES", 2)
    payload = _archive([("document.reqif", MINIMAL_REQIF), ("a.txt", b"a"), ("b.txt", b"b")])

    with pytest.raises(ReqIFParseError, match="archive entries"):
        parse_reqif(payload)


def test_uncompressed_member_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_MEMBER_BYTES", len(MINIMAL_REQIF) - 1)

    with pytest.raises(ReqIFParseError, match="uncompressed"):
        parse_reqif(_archive([("document.reqif", MINIMAL_REQIF)]))


def test_compression_ratio_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_COMPRESSION_RATIO", 20)
    payload = _archive(
        [("document.reqif", MINIMAL_REQIF + b" " * 100_000)],
        compression=zipfile.ZIP_DEFLATED,
    )

    with pytest.raises(ReqIFParseError, match="compression ratio"):
        parse_reqif(payload)


def test_encrypted_archive_member_is_rejected():
    info = zipfile.ZipInfo("document.reqif")
    info.flag_bits |= 0x1
    info.file_size = 1
    info.compress_size = 1

    with pytest.raises(ReqIFParseError, match="Encrypted"):
        _validate_member(info)


@pytest.mark.asyncio
async def test_parser_runs_in_a_killable_worker():
    bundle = await parse_reqif_in_worker(MINIMAL_REQIF, timeout_seconds=10)
    assert set(bundle.objects) == {"OBJ-1"}


@pytest.mark.asyncio
async def test_parser_worker_is_terminated_on_deadline():
    with pytest.raises(ReqIFProcessingTimeout):
        await parse_reqif_in_worker(MINIMAL_REQIF, timeout_seconds=0)


def _document(objects: bytes = b"", relations: bytes = b"", hierarchy: bytes = b"") -> bytes:
    return (
        b'<REQ-IF xmlns="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
        b"<CORE-CONTENT><REQ-IF-CONTENT><SPEC-OBJECTS>"
        + objects
        + b"</SPEC-OBJECTS><SPECIFICATIONS>"
        + hierarchy
        + b"</SPECIFICATIONS><SPEC-RELATIONS>"
        + relations
        + b"</SPEC-RELATIONS></REQ-IF-CONTENT></CORE-CONTENT></REQ-IF>"
    )


def test_object_limit_is_enforced_while_building(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_OBJECTS", 2)
    objects = b"".join(
        f'<SPEC-OBJECT IDENTIFIER="OBJ-{index}"><VALUES/></SPEC-OBJECT>'.encode()
        for index in range(3)
    )

    with pytest.raises(ReqIFParseError, match="object limit"):
        parse_reqif(_document(objects=objects))


def test_relation_limit_is_enforced_while_building(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_RELATIONS", 1)
    obj = b'<SPEC-OBJECT IDENTIFIER="OBJ"><VALUES/></SPEC-OBJECT>'
    relations = b"".join(
        (
            f'<SPEC-RELATION IDENTIFIER="REL-{index}">'
            "<SOURCE><SPEC-OBJECT-REF>OBJ</SPEC-OBJECT-REF></SOURCE>"
            "<TARGET><SPEC-OBJECT-REF>OBJ</SPEC-OBJECT-REF></TARGET>"
            "</SPEC-RELATION>"
        ).encode()
        for index in range(2)
    )

    with pytest.raises(ReqIFParseError, match="relation limit"):
        parse_reqif(_document(objects=obj, relations=relations))


def test_hierarchy_depth_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "REQIF_MAX_HIERARCHY_DEPTH", 2)
    hierarchy = (
        b'<SPECIFICATION IDENTIFIER="SPEC"><CHILDREN>'
        b"<SPEC-HIERARCHY><OBJECT><SPEC-OBJECT-REF>A</SPEC-OBJECT-REF></OBJECT><CHILDREN>"
        b"<SPEC-HIERARCHY><OBJECT><SPEC-OBJECT-REF>B</SPEC-OBJECT-REF></OBJECT><CHILDREN>"
        b"<SPEC-HIERARCHY><OBJECT><SPEC-OBJECT-REF>C</SPEC-OBJECT-REF></OBJECT>"
        b"</SPEC-HIERARCHY></CHILDREN></SPEC-HIERARCHY></CHILDREN></SPEC-HIERARCHY>"
        b"</CHILDREN></SPECIFICATION>"
    )

    with pytest.raises(ReqIFParseError, match="hierarchy depth"):
        parse_reqif(_document(hierarchy=hierarchy))


def test_repeated_ancestor_reference_is_rejected_as_hierarchy_cycle():
    hierarchy = (
        b'<SPECIFICATION IDENTIFIER="SPEC"><CHILDREN>'
        b"<SPEC-HIERARCHY><OBJECT><SPEC-OBJECT-REF>A</SPEC-OBJECT-REF></OBJECT><CHILDREN>"
        b"<SPEC-HIERARCHY><OBJECT><SPEC-OBJECT-REF>A</SPEC-OBJECT-REF></OBJECT>"
        b"</SPEC-HIERARCHY></CHILDREN></SPEC-HIERARCHY>"
        b"</CHILDREN></SPECIFICATION>"
    )

    with pytest.raises(ReqIFParseError, match="cycle"):
        parse_reqif(_document(hierarchy=hierarchy))
