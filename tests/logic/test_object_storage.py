"""S3 storage for attachments, against moto's in-process S3.

Covers the bucket round trip, the local mirror and its fallback, deletion, cleanup
of the bucket, the readiness answer and the migrate command.
"""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from moto import mock_aws
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import storage as storage_cli
from app.api.attachments import download_attachment
from app.core.config import Settings, settings
from app.core.database import Base
from app.models import Document, DocumentAttachment, Project
from app.models.user import User, UserRole
from app.services import attachment_cleanup, attachment_storage, object_store

BUCKET = "bloom-test"


@pytest.fixture
def s3(monkeypatch, tmp_path):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    for name, value in {
        "STORAGE_BACKEND": "s3",
        "STORAGE_LOCAL_MIRROR": True,
        "S3_BUCKET": BUCKET,
        "S3_REGION": "us-east-1",
        "S3_PREFIX": "bloom",
        "S3_ENDPOINT_URL": "",
        "ATTACHMENT_DIR": str(tmp_path / "attachments"),
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(attachment_storage, "_ROOT", None)
    object_store.client.cache_clear()
    with mock_aws():
        object_store.client().create_bucket(Bucket=BUCKET)
        yield object_store.client()
    object_store.client.cache_clear()


def _local(name: str, data: bytes = b"evidence"):
    path = attachment_storage.ensure_attachment_dir() / name
    path.write_bytes(data)
    return path


def _keys(client):
    return sorted(o["Key"] for o in client.list_objects_v2(Bucket=BUCKET).get("Contents", []))


async def test_persist_fetch_list_and_remove(s3):
    path = _local("a.txt")
    await attachment_storage.persist(path, "a.txt", "text/plain")
    assert path.exists()
    assert _keys(s3) == ["bloom/a.txt"]
    assert s3.head_object(Bucket=BUCKET, Key="bloom/a.txt")["ContentType"] == "text/plain"
    body = await object_store.fetch("a.txt")
    assert b"".join(object_store.iter_body(body)) == b"evidence"
    assert [o.name for o in await object_store.list_objects()] == ["a.txt"]
    assert await object_store.size_of("a.txt") == 8
    assert await object_store.size_of("nope.txt") is None
    assert await object_store.bucket_answers() is True

    await attachment_storage.remove("a.txt")
    assert _keys(s3) == [] and not path.exists()
    await attachment_storage.remove("a.txt")


async def test_without_the_mirror_the_local_file_goes(s3, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_LOCAL_MIRROR", False)
    path = _local("b.txt")
    await attachment_storage.persist(path, "b.txt", "text/plain")
    assert not path.exists() and _keys(s3) == ["bloom/b.txt"]


async def test_a_refused_upload_leaves_nothing(s3, monkeypatch):
    monkeypatch.setattr(settings, "S3_BUCKET", "no-such-bucket")
    path = _local("c.txt")
    with pytest.raises(HTTPException) as refused:
        await attachment_storage.persist(path, "c.txt", "text/plain")
    assert refused.value.status_code == 503 and not path.exists()
    assert await object_store.bucket_answers() is False


async def test_local_storage_is_untouched(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "ATTACHMENT_DIR", str(tmp_path))
    monkeypatch.setattr(attachment_storage, "_ROOT", None)
    path = _local("d.txt")
    await attachment_storage.persist(path, "d.txt", "text/plain")
    assert path.exists() and object_store.keeps_local_copy()
    assert object_store.object_key("d.txt") == "bloom/d.txt"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        project = Project(name="Alpha", prefix="ALP")
        session.add(project)
        admin = User(email="a@x.test", full_name="Ada", hashed_password="x", role=UserRole.admin)
        session.add(admin)
        await session.flush()
        document = Document(
            project_id=project.id, doc_id="ALP-SPEC-001", title="Spec", doc_type="SPEC"
        )
        session.add(document)
        await session.flush()
        yield session, document, admin
    await engine.dispose()


async def _attachment(session, document, name):
    row = DocumentAttachment(
        document_id=document.id,
        filename=name,
        original_filename="report.txt",
        content_type="text/plain",
        size_bytes=8,
        sha256="x",
        storage_path=name,
    )
    session.add(row)
    await session.commit()
    return row


async def _read(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
    return b"".join(chunks)


async def test_download_streams_from_the_bucket_and_falls_back(s3, db, monkeypatch):
    session, document, admin = db
    path = _local("e.txt")
    await attachment_storage.persist(path, "e.txt", "text/plain")
    row = await _attachment(session, document, "e.txt")

    response = await download_attachment(row.id, db=session, current_user=admin)
    assert await _read(response) == b"evidence"
    assert response.headers["content-disposition"].startswith("attachment;")

    s3.delete_object(Bucket=BUCKET, Key="bloom/e.txt")
    fallback = await download_attachment(row.id, db=session, current_user=admin)
    assert fallback.path == str(path)

    path.unlink()
    with pytest.raises(HTTPException) as gone:
        await download_attachment(row.id, db=session, current_user=admin)
    assert gone.value.status_code == 503


async def test_cleanup_reconciles_the_bucket(s3, db, monkeypatch):
    session, document, _ = db
    for name in ("kept.txt", "orphan.txt"):
        await attachment_storage.persist(_local(name), name, "text/plain")
    await _attachment(session, document, "kept.txt")
    await _attachment(session, document, "missing.txt")

    report = await attachment_cleanup.reconcile_attachments(session, orphan_grace_seconds=-60)
    assert _keys(s3) == ["bloom/kept.txt"]
    assert report.missing_files == 1
    assert report.orphan_files == 2

    monkeypatch.setattr(settings, "STORAGE_LOCAL_MIRROR", False)
    await object_store.put_file(_local("late.txt"), "late.txt", "text/plain")
    again = await attachment_cleanup.reconcile_attachments(session, orphan_grace_seconds=-60)
    assert again.orphan_files == 1 and _keys(s3) == ["bloom/kept.txt"]


async def test_migrate_copies_once_and_checks_sizes(s3, monkeypatch, capsys):
    _local("m1.txt")
    _local("m2.txt", b"longer evidence")
    _local(".attachment-part.part")
    assert await storage_cli.migrate_to_s3() == (2, 0, [])
    assert _keys(s3) == ["bloom/m1.txt", "bloom/m2.txt"]
    assert await storage_cli.migrate_to_s3() == (0, 2, [])

    real_size = object_store.size_of
    _local("m3.txt")

    async def wrong_size(name):
        return 1 if name == "m3.txt" else await real_size(name)

    monkeypatch.setattr(object_store, "size_of", wrong_size)
    assert await storage_cli.migrate_to_s3() == (0, 2, ["m3.txt"])


def test_migrate_command(s3, monkeypatch, capsys):
    monkeypatch.setattr(storage_cli, "migrate_to_s3", _fake_migrate((1, 2, [])))
    assert storage_cli.main(["migrate", "--to", "s3"]) == 0
    assert "copied 1, already there 2, size mismatches 0" in capsys.readouterr().out
    monkeypatch.setattr(storage_cli, "migrate_to_s3", _fake_migrate((0, 0, ["x.txt"])))
    assert storage_cli.main(["migrate", "--to", "s3"]) == 1
    assert "size mismatch: x.txt" in capsys.readouterr().err
    monkeypatch.setattr(settings, "S3_BUCKET", "")
    assert storage_cli.main(["migrate", "--to", "s3"]) == 2


def _fake_migrate(result):
    async def fake():
        return result

    return fake


def test_s3_needs_a_bucket():
    with pytest.raises(ValueError, match="needs S3_BUCKET"):
        Settings(STORAGE_BACKEND="s3", S3_BUCKET="", SECRET_KEY="x" * 40)
    assert Settings(STORAGE_BACKEND="s3", S3_BUCKET="b", SECRET_KEY="x" * 40).S3_PREFIX == "bloom"


def test_client_options(monkeypatch):
    object_store.client.cache_clear()
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "http://minio.local:9000")
    monkeypatch.setattr(settings, "S3_REGION", "eu-central-1")
    monkeypatch.setattr(settings, "S3_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(settings, "S3_SECRET_ACCESS_KEY", "secret")
    made = object_store.client()
    assert made.meta.endpoint_url == "http://minio.local:9000"
    assert made.meta.region_name == "eu-central-1"
    object_store.client.cache_clear()
    monkeypatch.setattr(settings, "S3_PREFIX", "")
    assert object_store.object_key("f.txt") == "f.txt"
    assert object_store._name_of("f.txt") == "f.txt"
