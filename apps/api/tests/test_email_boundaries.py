"""Transport boundary tests: none of these sends real email or proves delivery."""

import json
import smtplib
from types import SimpleNamespace

import pytest
from app.core.errors import AppError
from app.services import email_sender


def message(recipient="fixture@example.com"):
    return email_sender.OutboundEmail(
        recipient, "Verification fixture", "Synthetic test body", "123456"
    )


def settings(**changes):
    return SimpleNamespace(
        smtp_host="fixture.invalid",
        smtp_port=587,
        smtp_from="sender@example.com",
        smtp_tls=True,
        smtp_username="fixture",
        smtp_password="test-transport-password",
        app_env="production",
        **changes,
    )


@pytest.mark.parametrize("tls,authenticate", [(True, True), (False, False)])
def test_smtp_builds_expected_message_and_honors_transport_security(monkeypatch, tls, authenticate):
    config = settings()
    config.smtp_tls = tls
    config.smtp_username = "fixture" if authenticate else None
    events = []

    class SMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("fixture.invalid", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            events.append("tls")

        def login(self, user, password):
            assert user == "fixture" and password == config.smtp_password
            events.append("login")

        def send_message(self, email):
            assert email["From"] == config.smtp_from
            assert email["To"] == "fixture@example.com"
            assert email["Subject"] == "Verification fixture"
            assert email.get_content().strip() == "Synthetic test body"
            events.append("submitted")

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    email_sender.SmtpEmailSender(config).send(message())
    assert events == (["tls"] if tls else []) + (["login"] if authenticate else []) + ["submitted"]


@pytest.mark.parametrize(
    "failure",
    [
        OSError("connection refused"),
        smtplib.SMTPAuthenticationError(535, b"test refusal"),
        smtplib.SMTPRecipientsRefused({"fixture@example.com": (550, b"test refusal")}),
    ],
)
def test_smtp_failure_cannot_be_reported_as_delivery(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(smtplib, "SMTP", fail)
    with pytest.raises(AppError) as caught:
        email_sender.SmtpEmailSender(settings()).send(message())
    assert caught.value.status_code == 503
    assert caught.value.code == "email_delivery_failed"


def test_missing_smtp_never_falls_back_to_production_mailbox(tmp_path):
    config = settings()
    config.smtp_host = None
    config.mailbox_file = tmp_path / "forbidden-mailbox"
    with pytest.raises(AppError, match="Production email requires"):
        email_sender.build_email_sender(config)
    with pytest.raises(AppError, match="Email delivery is not configured"):
        email_sender.SmtpEmailSender(config).send(message())
    assert not config.mailbox_file.exists()


def test_development_mailbox_persists_latest_recipient_without_cross_user_leak(tmp_path):
    config = settings()
    config.smtp_host = None
    config.app_env = "development"
    config.mailbox_file = tmp_path / "isolated" / "mailbox.jsonl"
    assert email_sender.latest_mailbox_message(config.mailbox_file, "fixture@example.com") is None
    sender = email_sender.build_email_sender(config)
    sender.send(message())
    other = message("other@example.com")
    other.code = "654321"
    sender.send(other)
    with config.mailbox_file.open("a") as output:
        output.write("\n")
    row = email_sender.latest_mailbox_message(config.mailbox_file, "fixture@example.com")
    assert row["code"] == "123456" and row["recipient"] == "fixture@example.com"
    assert (
        email_sender.latest_mailbox_message(config.mailbox_file, "other@example.com")["code"]
        == "654321"
    )
    assert email_sender.latest_mailbox_message(config.mailbox_file, "absent@example.com") is None
    assert all(
        json.loads(line)["created_at"]
        for line in config.mailbox_file.read_text().splitlines()
        if line
    )
    config.app_env = "test"
    capture = email_sender.build_email_sender(config)
    capture.send(message())
    assert capture.messages[0].recipient == "fixture@example.com"
    config.smtp_host = "fixture.invalid"
    assert isinstance(email_sender.build_email_sender(config), email_sender.SmtpEmailSender)
