"""Files held against a document, and the Bud reports published as RPT documents."""

from __future__ import annotations

import asyncio
import base64
import os
import threading
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from tests.conftest import create_project, unique_email  # noqa: E402

PDF = b"%PDF-1.4 fake report"
XML = b"<testsuites><testsuite name='s'/></testsuites>"


@pytest.fixture(autouse=True)
def generous_attachment_request_limit(monkeypatch):
    """Keep unrelated attachment tests independent of the public request default."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ATTACHMENT_UPLOADS_PER_15_MINUTES", 100)


@pytest.fixture
def auth_headers(api_client: TestClient):
    from app.core.config import settings

    login = api_client.post(
        "/api/auth/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def project(api_client: TestClient, auth_headers):
    return create_project(api_client, auth_headers, "Attach")


@pytest.fixture
def document(api_client: TestClient, auth_headers, project):
    response = api_client.post(
        f"/api/projects/{project['id']}/documents",
        headers=auth_headers,
        json={"project_id": project["id"], "doc_type": "RPT", "title": "Bus report"},
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.fixture
def bud_token(api_client: TestClient, auth_headers):
    response = api_client.post(
        "/api/service-credentials",
        headers=auth_headers,
        json={"name": "bud-publish", "expires_in_days": 30},
    )
    assert response.status_code in (200, 201), response.text
    return response.json()["token"]


def _upload(api_client, headers, document_id, name, payload, content_type):
    return api_client.post(
        f"/api/documents/{document_id}/attachments",
        headers=headers,
        files={"file": (name, payload, content_type)},
    )


def _maintainer_headers(api_client, admin_headers, project):
    email = unique_email("attachment-maintainer")
    password = "Attachment-Maintainer-123"
    created = api_client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": email,
            "full_name": "Attachment Maintainer",
            "password": password,
            "role": "maintainer",
        },
    )
    assert created.status_code == 201, created.text
    assigned = api_client.post(
        f"/api/projects/{project['id']}/members",
        headers=admin_headers,
        json={"user_id": created.json()["id"], "role": "maintainer"},
    )
    assert assigned.status_code == 201, assigned.text
    login = api_client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class TestHoldingFilesAgainstADocument:
    def test_rate_limits_upload_starts_per_maintainer(
        self, api_client, auth_headers, project, document, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "ATTACHMENT_UPLOADS_PER_15_MINUTES", 2)
        maintainer_headers = _maintainer_headers(api_client, auth_headers, project)

        first = _upload(
            api_client, maintainer_headers, document["id"], "first.pdf", PDF, "application/pdf"
        )
        second = _upload(
            api_client, maintainer_headers, document["id"], "second.pdf", PDF, "application/pdf"
        )
        rejected = _upload(
            api_client, maintainer_headers, document["id"], "third.pdf", PDF, "application/pdf"
        )

        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert rejected.status_code == 429, rejected.text
        assert rejected.headers["retry-after"] == "900"

    def test_only_one_attachment_upload_is_active_per_maintainer(
        self, api_client, auth_headers, project, document, monkeypatch
    ):
        from app.services import attachment_storage

        maintainer_headers = _maintainer_headers(api_client, auth_headers, project)
        entered = threading.Event()
        release = threading.Event()
        call_lock = threading.Lock()
        calls = 0
        original = attachment_storage.write_stream

        async def controlled_write(file, final_path, *, max_bytes):
            nonlocal calls
            with call_lock:
                calls += 1
                position = calls
            if position == 1:
                entered.set()
                while not release.is_set():
                    await asyncio.sleep(0.01)
            return await original(file, final_path, max_bytes=max_bytes)

        monkeypatch.setattr(attachment_storage, "write_stream", controlled_write)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(
                _upload,
                api_client,
                maintainer_headers,
                document["id"],
                "slow.pdf",
                PDF,
                "application/pdf",
            )
            assert entered.wait(timeout=10), "first upload never reached storage"
            second_future = pool.submit(
                _upload,
                api_client,
                maintainer_headers,
                document["id"],
                "racing.pdf",
                PDF,
                "application/pdf",
            )
            try:
                second = second_future.result(timeout=10)
            finally:
                release.set()
            first = first_future.result(timeout=10)

        assert sorted([first.status_code, second.status_code]) == [201, 429]
        rejected = first if first.status_code == 429 else second
        assert rejected.headers["retry-after"] == "60"

    def test_stores_and_lists_a_file(self, api_client, auth_headers, document):
        created = _upload(
            api_client, auth_headers, document["id"], "report.pdf", PDF, "application/pdf"
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["original_filename"] == "report.pdf"
        assert body["size_bytes"] == len(PDF)

        listed = api_client.get(
            f"/api/documents/{document['id']}/attachments", headers=auth_headers
        )
        assert [item["id"] for item in listed.json()] == [body["id"]]

    def test_the_bytes_come_back(self, api_client, auth_headers, document):
        created = _upload(
            api_client, auth_headers, document["id"], "report.pdf", PDF, "application/pdf"
        ).json()

        got = api_client.get(f"/api/attachments/{created['id']}/download", headers=auth_headers)

        assert got.status_code == 200
        assert got.content == PDF
        # Never inline: a stored SVG would otherwise run in the reader's session.
        assert "attachment" in got.headers["content-disposition"]
        assert got.headers["x-content-type-options"] == "nosniff"

    def test_the_stored_name_is_never_the_one_supplied(self, api_client, auth_headers, document):
        created = _upload(
            api_client,
            auth_headers,
            document["id"],
            "../../etc/passwd.pdf",
            PDF,
            "application/pdf",
        )

        assert created.status_code == 201, created.text
        # The path is discarded; what is shown is a name, not a location.
        assert "/" not in created.json()["original_filename"]

    def test_refuses_a_type_that_is_not_allowed(self, api_client, auth_headers, document):
        rejected = _upload(
            api_client, auth_headers, document["id"], "run.exe", b"MZ", "application/x-msdownload"
        )
        assert rejected.status_code == 415

    def test_records_a_digest_of_what_was_stored(self, api_client, auth_headers, document):
        import hashlib

        created = _upload(
            api_client, auth_headers, document["id"], "report.pdf", PDF, "application/pdf"
        ).json()
        assert created["sha256"] == hashlib.sha256(PDF).hexdigest()

    def test_removing_it_removes_the_file(self, api_client, auth_headers, document):
        created = _upload(
            api_client, auth_headers, document["id"], "report.pdf", PDF, "application/pdf"
        ).json()

        removed = api_client.delete(f"/api/attachments/{created['id']}", headers=auth_headers)
        assert removed.status_code == 204

        listed = api_client.get(
            f"/api/documents/{document['id']}/attachments", headers=auth_headers
        )
        assert listed.json() == []

    def test_a_missing_document_is_not_found(self, api_client, auth_headers):
        response = api_client.get("/api/documents/999999/attachments", headers=auth_headers)
        assert response.status_code == 404

    def test_reading_requires_authentication(self, api_client, document):
        assert api_client.get(f"/api/documents/{document['id']}/attachments").status_code == 401


class TestPublishingABudReport:
    def _publish(self, api_client, token, project, run_id=41, files=None, name="Nightly HIL"):
        return api_client.post(
            "/api/bud/test-reports",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_prefix": project["prefix"],
                "bud_run_id": run_id,
                "run_name": name,
                "status": "Completed",
                "total_tests": 3,
                "passed_tests": 2,
                "failed_tests": 1,
                "run_url": "https://bud.test/test-runs/41",
                "tc_ids": ["VCU-TC-001"],
                "files": (
                    files
                    if files is not None
                    else [
                        {
                            "filename": "bud-run-41.pdf",
                            "content_type": "application/pdf",
                            "content_base64": base64.b64encode(PDF).decode(),
                        },
                        {
                            "filename": "report_junit.xml",
                            "content_type": "application/xml",
                            "content_base64": base64.b64encode(XML).decode(),
                        },
                    ]
                ),
            },
        )

    def test_creates_a_report_document_carrying_both_files(
        self, api_client, auth_headers, bud_token, project
    ):
        response = self._publish(api_client, bud_token, project)

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["created"] is True
        assert body["doc_id"].startswith(f"{project['prefix']}-RPT-")

        listed = api_client.get(
            f"/api/documents/{body['document_id']}/attachments", headers=auth_headers
        )
        assert sorted(item["original_filename"] for item in listed.json()) == [
            "bud-run-41.pdf",
            "report_junit.xml",
        ]

    def test_it_lands_as_an_rpt_document_in_the_registry(
        self, api_client, auth_headers, bud_token, project
    ):
        self._publish(api_client, bud_token, project)

        docs = api_client.get(
            f"/api/projects/{project['prefix']}/docs",
            headers=auth_headers,
            params={"type": "RPT"},
        ).json()

        assert [item["doc_type"] for item in docs["items"]] == ["RPT"]

    def test_the_summary_records_the_outcome(self, api_client, auth_headers, bud_token, project):
        body = self._publish(api_client, bud_token, project).json()

        document = api_client.get(
            f"/api/documents/{body['document_id']}", headers=auth_headers
        ).json()

        assert "2 passed, 1 failed" in document["description"]
        assert "VCU-TC-001" in document["description"]
        assert "https://bud.test/test-runs/41" in document["description"]

    def test_publishing_the_same_run_again_updates_it(
        self, api_client, auth_headers, bud_token, project
    ):
        """A nightly suite must not mint a Report a night, and a retry is safe."""
        first = self._publish(api_client, bud_token, project).json()
        second = self._publish(api_client, bud_token, project, name="Nightly HIL rerun").json()

        assert second["created"] is False
        assert second["document_id"] == first["document_id"]

        listed = api_client.get(
            f"/api/documents/{first['document_id']}/attachments", headers=auth_headers
        ).json()
        # Replaced, not appended.
        assert len(listed) == 2

    def test_a_different_run_gets_its_own_document(
        self, api_client, auth_headers, bud_token, project
    ):
        first = self._publish(api_client, bud_token, project, run_id=41).json()
        second = self._publish(api_client, bud_token, project, run_id=42).json()

        assert second["created"] is True
        assert second["document_id"] != first["document_id"]

    def test_rejects_content_that_is_not_base64(self, api_client, bud_token, project):
        response = self._publish(
            api_client,
            bud_token,
            project,
            files=[
                {
                    "filename": "broken.pdf",
                    "content_type": "application/pdf",
                    "content_base64": "not base64 at all!!",
                }
            ],
        )
        assert response.status_code == 422

    def test_refuses_a_file_type_that_is_not_allowed(self, api_client, bud_token, project):
        response = self._publish(
            api_client,
            bud_token,
            project,
            files=[
                {
                    "filename": "payload.exe",
                    "content_type": "application/x-msdownload",
                    "content_base64": base64.b64encode(b"MZ").decode(),
                }
            ],
        )
        assert response.status_code == 415

    def test_an_unknown_project_is_not_found(self, api_client, bud_token):
        response = api_client.post(
            "/api/bud/test-reports",
            headers={"Authorization": f"Bearer {bud_token}"},
            json={
                "project_prefix": "NOPE",
                "bud_run_id": 1,
                "run_name": "x",
                "files": [],
            },
        )
        assert response.status_code == 404

    def test_a_user_token_cannot_publish(self, api_client, auth_headers, project):
        """Publishing is a service call; a browser session is not Bud."""
        response = api_client.post(
            "/api/bud/test-reports",
            headers=auth_headers,
            json={
                "project_prefix": project["prefix"],
                "bud_run_id": 1,
                "run_name": "x",
                "files": [],
            },
        )
        assert response.status_code == 401

    def test_publishing_requires_a_credential(self, api_client, project):
        response = api_client.post(
            "/api/bud/test-reports",
            json={
                "project_prefix": project["prefix"],
                "bud_run_id": 1,
                "run_name": "x",
                "files": [],
            },
        )
        assert response.status_code == 401
