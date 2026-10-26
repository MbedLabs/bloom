import os
import re

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


def _configure_smtp(monkeypatch, *, starttls=True, port=2525):
    monkeypatch.setattr(mail_service.settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(mail_service.settings, "SMTP_HOST", "mail")
    monkeypatch.setattr(mail_service.settings, "SMTP_PORT", port)
    monkeypatch.setattr(mail_service.settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(mail_service.settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(mail_service.settings, "SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setattr(mail_service.settings, "SMTP_REPLY_TO", None)
    monkeypatch.setattr(mail_service.settings, "SMTP_STARTTLS", starttls)
    monkeypatch.setattr(mail_service.settings, "SMTP_SSL", False)
    monkeypatch.setattr(mail_service.settings, "SMTP_TIMEOUT_SECONDS", 9)


def test_starttls_on_a_plaintext_port_reports_where_and_why(monkeypatch):
    """The exact production failure: STARTTLS asked of a relay that does not offer it."""
    import smtplib

    class _NoStartTLS(_DummySMTP):
        def starttls(self):
            raise smtplib.SMTPNotSupportedError("STARTTLS extension not supported by server.")

    _configure_smtp(monkeypatch, starttls=True, port=2525)
    monkeypatch.setattr(
        mail_service.smtplib, "SMTP", lambda host, port, timeout: _NoStartTLS(host, port, timeout)
    )

    try:
        mail_service.send_email(to_email="someone@example.com", subject="s", text_body="t")
    except mail_service.MailDeliveryError as exc:
        message = str(exc)
    else:
        raise AssertionError("a failing STARTTLS handshake must not look like success")

    assert "mail:2525" in message
    assert "STARTTLS=True" in message
    assert "SMTPNotSupportedError" in message


def test_delivery_failures_reach_the_existing_error_handlers(monkeypatch):
    """Every endpoint already maps MailConfigurationError to a 503 carrying the
    message. MailDeliveryError subclasses it so transport failures take that same
    path instead of escaping as an empty 500."""
    assert issubclass(mail_service.MailDeliveryError, mail_service.MailConfigurationError)


def test_an_unreachable_relay_is_also_reported(monkeypatch):
    """OSError, not SMTPException: a refused connection must be translated too."""
    _configure_smtp(monkeypatch, starttls=False, port=2525)

    def _refused(host, port, timeout):
        raise OSError("Connection refused")

    monkeypatch.setattr(mail_service.smtplib, "SMTP", _refused)

    try:
        mail_service.send_email(to_email="a@example.com", subject="s", text_body="t")
    except mail_service.MailDeliveryError as exc:
        assert "mail:2525" in str(exc)
    else:
        raise AssertionError("an unreachable relay must raise MailDeliveryError")


def test_delivery_log_excludes_message_and_recipient(monkeypatch, caplog):
    """Successful deliveries keep recipient and message content out of logs."""
    import logging

    _configure_smtp(monkeypatch, starttls=False)
    monkeypatch.setattr(mail_service.smtplib, "SMTP", _DummySMTP)
    with caplog.at_level(logging.INFO, logger=mail_service.__name__):
        mail_service.send_email(
            to_email="private-recipient@example.com",
            subject="Private subject with an untrusted marker",
            text_body="private message content",
        )
    assert "Email sent" in caplog.text
    assert "private-recipient" not in caplog.text
    assert "untrusted marker" not in caplog.text
    assert "private message content" not in caplog.text


def test_delivery_error_log_excludes_untrusted_server_response(monkeypatch, caplog):
    """SMTP errors retain diagnostic exceptions without logging server text."""
    import logging
    import smtplib

    import pytest

    _configure_smtp(monkeypatch, starttls=False)

    def refused(host, port, timeout):
        raise smtplib.SMTPException("remote response\nforged log entry")

    monkeypatch.setattr(mail_service.smtplib, "SMTP", refused)
    with caplog.at_level(logging.ERROR, logger=mail_service.__name__):
        with pytest.raises(mail_service.MailDeliveryError) as error:
            mail_service.send_email(
                to_email="private-recipient@example.com", subject="private", text_body="body"
            )
    assert "SMTPException" in caplog.text
    assert "remote response" not in caplog.text
    assert "forged log entry" not in caplog.text
    assert "remote response" in str(error.value)


def test_workflow_request_uses_matching_branded_html_and_text(monkeypatch):
    """Workflow mail renders the product shell and keeps untrusted fields as text."""
    messages = []
    monkeypatch.setattr(mail_service, "send_email", lambda **message: messages.append(message))
    mail_service.send_workflow_request_email(
        to_email="reviewer@example.com",
        recipient_name="Reviewer & partner",
        actor_name="Writer <script>alert(1)</script>",
        event_title="Review requested: PRJ-REQ-001",
        document_link="https://bloom.example.com/projects/PRJ/docs/requirements/PRJ-REQ-001?one=1&two=2",
    )
    assert len(messages) == 1
    message = messages[0]
    assert message["subject"] == "Review requested: PRJ-REQ-001"
    assert message["to_email"] == "reviewer@example.com"
    assert "Reviewer & partner" in message["text_body"]
    assert "Writer <script>alert(1)</script>" in message["text_body"]
    assert "Review requested: PRJ-REQ-001" in message["text_body"]
    assert "Bloom PLM by EmbedLabs" in message["text_body"]
    assert "<title>Bloom PLM by EmbedLabs</title>" in message["html_body"]
    assert "background:#8925d0" in message["html_body"]
    assert "background:#ffffff" in message["html_body"]
    assert "Reviewer &amp; partner" in message["html_body"]
    assert "Writer &lt;script&gt;alert(1)&lt;/script&gt;" in message["html_body"]
    assert "<script>" not in message["html_body"]
    assert 'one=1&amp;two=2"' in message["html_body"]
    assert "Open document" in message["html_body"]
    assert ">Bloom PLM by EmbedLabs</h1>" in message["html_body"]
    next_step = "View the discussion and document status in Bloom PLM."
    assert next_step in message["html_body"]
    assert next_step in message["text_body"]
    assert message["text_body"].startswith("Bloom PLM by EmbedLabs\n")
    assert message["html_body"].count("<a href=") == 1
    assert "${" not in message["html_body"]
    assert "${" not in message["text_body"]


def test_access_request_uses_bloom_identity_and_matching_next_steps(monkeypatch):
    """Access requests use the Bloom product shell with one action and matching instructions."""
    messages = []
    monkeypatch.setattr(mail_service, "send_email", lambda **message: messages.append(message))
    mail_service.send_access_request_email(
        to_email="admin@example.com",
        admin_name="Administrator",
        requester_name="Writer <script>",
        requester_email="writer@example.com",
        resource="PRJ-REQ-001",
        project="PRJ",
        requested_at="2026-10-25T10:00:00Z",
        request_id="42",
        review_link="https://bloom.example.com/access",
    )
    message = messages[0]
    assert message["subject"] == "Access requested on Bloom PLM: PRJ-REQ-001"
    assert ">Bloom PLM by EmbedLabs</h1>" in message["html_body"]
    assert message["text_body"].startswith("Bloom PLM by EmbedLabs\n")
    next_step = "Grant access in Bloom PLM, then mark the request granted or refused."
    assert next_step in message["html_body"]
    assert next_step in message["text_body"]
    assert message["html_body"].count("<a href=") == 1
    assert "Writer &lt;script&gt;" in message["html_body"]
    assert "Writer <script>" in message["text_body"]


def _every_bloom_mail(monkeypatch):
    """Render each Bloom email through the mail service and return the captured messages."""
    messages = []
    monkeypatch.setattr(mail_service, "send_email", lambda **message: messages.append(message))
    link = "https://bloom.example.com/link#token"
    mail_service.send_invite_email(to_email="a@example.com", full_name="Ada", invite_link=link)
    mail_service.send_verification_email(
        to_email="a@example.com", full_name="Ada", verification_link=link
    )
    mail_service.send_password_reset_email(
        to_email="a@example.com", full_name="Ada", reset_link=link
    )
    mail_service.send_admin_welcome_email(
        to_email="a@example.com", full_name="Ada", login_link=link
    )
    for send in (
        mail_service.send_email_change_email,
        mail_service.send_email_change_authorization_email,
    ):
        send(
            to_email="a@example.com",
            full_name="Ada",
            old_email="old@example.com",
            new_email="new@example.com",
            confirm_link=link,
        )
    mail_service.send_access_request_email(
        to_email="a@example.com",
        admin_name="Admin",
        requester_name="Ada",
        requester_email="ada@example.com",
        resource="PRJ-REQ-001",
        project="PRJ",
        requested_at="2026-10-25T10:00:00Z",
        request_id="1",
        review_link=link,
    )
    mail_service.send_workflow_request_email(
        to_email="a@example.com",
        recipient_name="Ada",
        actor_name="Writer",
        event_title="Review requested: PRJ-REQ-001",
        document_link=link,
    )
    return messages


def test_every_bloom_email_follows_the_product_structure(monkeypatch):
    """Each email is headed by the product identity and carries one action link in both formats."""
    messages = _every_bloom_mail(monkeypatch)
    assert len(messages) == 8
    for message in messages:
        html_body, text_body = message["html_body"], message["text_body"]
        assert "<title>Bloom PLM by EmbedLabs</title>" in html_body
        assert re.search(r"<h1[^>]*>(Welcome to )?Bloom PLM by EmbedLabs</h1>", html_body)
        assert html_body.count("<a href=") == 1
        assert "https://bloom.example.com/link#token" in html_body
        assert "https://bloom.example.com/link#token" in text_body
        assert "Bloom PLM" in text_body
        assert "&copy; 2026 EmbedLabs. All rights reserved." in html_body
        assert "(c) 2026 EmbedLabs. All rights reserved." in text_body
        assert "EmbedLabs Bloom" not in html_body + text_body + message["subject"]
        assert "${" not in html_body + text_body
