"""Bloom names itself Bloom PLM by EmbedLabs, and no setting or environment value renames it."""

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.core.config import Settings
from app.core.identity import POWERED_BY, PRODUCT_IDENTITY, PRODUCT_NAME
from app.services import mail_service

ROOT = Path(__file__).resolve().parents[2]


def _capture_mail(monkeypatch):
    """Replace delivery with a list that collects every message the mail service sends."""
    sent = []

    def _send_email(*, to_email, subject, text_body, html_body=None):
        sent.append({"to": to_email, "subject": subject, "text": text_body, "html": html_body})

    monkeypatch.setattr(mail_service, "send_email", _send_email)
    return sent


def test_identity_constants():
    assert PRODUCT_NAME == "Bloom PLM"
    assert PRODUCT_IDENTITY == "Bloom PLM by EmbedLabs"
    assert POWERED_BY == "Powered by EmbedLabs"


def test_invite_email_names_bloom_plm(monkeypatch):
    sent = _capture_mail(monkeypatch)
    mail_service.send_invite_email(
        to_email="ada@example.com", full_name="Ada", invite_link="https://bloom.example/i#t"
    )
    assert sent[0]["subject"] == "You're invited to Bloom PLM"
    assert "<title>Bloom PLM by EmbedLabs</title>" in sent[0]["html"]
    assert "Welcome to Bloom PLM by EmbedLabs</h1>" in sent[0]["html"]
    assert "join the Bloom PLM platform" in sent[0]["text"]


def test_access_request_email_carries_the_identity(monkeypatch):
    sent = _capture_mail(monkeypatch)
    mail_service.send_access_request_email(
        to_email="admin@example.com",
        admin_name="Admin",
        requester_name="Ada",
        requester_email="ada@example.com",
        resource="Requirements",
        project="PRJ",
        requested_at="2026-10-19 10:00 UTC",
        request_id="7",
        review_link="https://bloom.example/access",
    )
    assert sent[0]["subject"] == "Access requested on Bloom PLM: Requirements"
    assert "<title>Bloom PLM by EmbedLabs</title>" in sent[0]["html"]
    assert "${app_identity}" not in sent[0]["html"]


def test_email_change_authorization_names_bloom_plm(monkeypatch):
    sent = _capture_mail(monkeypatch)
    mail_service.send_email_change_authorization_email(
        to_email="admin@example.com",
        full_name="Admin",
        old_email="admin@example.com",
        new_email="new@example.com",
        confirm_link="https://bloom.example/c#t",
    )
    assert "Bloom PLM will send a separate verification link" in sent[0]["text"]
    assert "Bloom PLM will send a separate verification link" in sent[0]["html"]


def test_api_title_is_the_fixed_identity():
    from app.main import app

    assert app.title == "Bloom PLM by EmbedLabs"
    assert app.description == "Backend API for Bloom PLM by EmbedLabs"


def test_app_name_is_not_a_setting(monkeypatch, tmp_path):
    monkeypatch.delenv("BLOOM_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("BLOOM_APP_NAME", "Renamed")
    env_file = tmp_path / ".env"
    env_file.write_text("BLOOM_APP_NAME=Renamed from dotenv\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert "BLOOM_APP_NAME" not in Settings.model_fields
    assert not hasattr(settings, "BLOOM_APP_NAME")


def test_app_name_in_the_environment_does_not_rename_the_app():
    env = {**os.environ, "BLOOM_APP_NAME": "Renamed", "BLOOM_DOTENV_DISABLED": "1"}
    result = subprocess.run(
        [sys.executable, "-c", "from app.main import app; print(app.title)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    assert result.stdout.strip().splitlines()[-1] == "Bloom PLM by EmbedLabs"
