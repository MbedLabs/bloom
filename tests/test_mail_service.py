import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-at-least-32-characters-long")

from app.services import mail_service


class _DummySMTP:
    def __init__(self, host: str, port: int, timeout: int):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = None
        self.messages = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, username: str, password: str):
        self.logged_in = (username, password)

    def send_message(self, message):
        self.messages.append(message)


def test_send_email_uses_fixed_bloom_sender_name(monkeypatch):
    captured = {}

    def smtp_factory(host: str, port: int, timeout: int):
        smtp = _DummySMTP(host, port, timeout)
        captured["smtp"] = smtp
        return smtp

    monkeypatch.setattr(mail_service.settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(mail_service.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(mail_service.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(mail_service.settings, "SMTP_USERNAME", "smtp-user")
    monkeypatch.setattr(mail_service.settings, "SMTP_PASSWORD", "smtp-password")
    monkeypatch.setattr(mail_service.settings, "SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(mail_service.settings, "SMTP_REPLY_TO", None)
    monkeypatch.setattr(mail_service.settings, "SMTP_STARTTLS", True)
    monkeypatch.setattr(mail_service.settings, "SMTP_SSL", False)
    monkeypatch.setattr(mail_service.settings, "SMTP_TIMEOUT_SECONDS", 9)
    monkeypatch.setattr(mail_service.smtplib, "SMTP", smtp_factory)

    mail_service.send_email(
        to_email="user@example.com",
        subject="Test subject",
        text_body="plain text",
        html_body="<p>plain text</p>",
    )

    smtp = captured["smtp"]
    assert smtp.host == "smtp.example.com"
    assert smtp.port == 587
    assert smtp.timeout == 9
    assert smtp.started_tls is True
    assert smtp.logged_in == ("smtp-user", "smtp-password")
    assert len(smtp.messages) == 1
    assert smtp.messages[0]["From"] == "Bloom PLM by EmbedLabs <noreply@example.com>"
