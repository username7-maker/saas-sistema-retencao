import httpx

from app.utils import email as email_utils


def test_send_email_result_is_blocked_without_resend_api_key(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "resend_api_key", "")
    monkeypatch.setattr(email_utils, "_email_provider_block_reason", None)

    result = email_utils.send_email_result("member@example.com", "Subject", "Body")

    assert result.sent is False
    assert result.blocked is True
    assert result.reason == "resend_api_key_missing"


def test_send_email_result_posts_to_resend(monkeypatch):
    observed = {}
    monkeypatch.setattr(email_utils.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(email_utils.settings, "resend_sender", "Cordex Gym OS <onboarding@resend.dev>")
    monkeypatch.setattr(email_utils.settings, "resend_reply_to", "automai904@gmail.com")
    monkeypatch.setattr(email_utils, "_email_provider_block_reason", None)

    def fake_post(url, *, headers, json, timeout):
        observed.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return httpx.Response(200, json={"id": "email-123"})

    monkeypatch.setattr(email_utils.httpx, "post", fake_post)

    result = email_utils.send_email_result("member@example.com", "Subject", "Body")

    assert result.sent is True
    assert observed["url"] == email_utils.RESEND_EMAILS_URL
    assert observed["headers"]["Authorization"] == "Bearer test-key"
    assert observed["json"]["from"] == "Cordex Gym OS <onboarding@resend.dev>"
    assert observed["json"]["to"] == ["member@example.com"]
    assert observed["json"]["reply_to"] == "automai904@gmail.com"
    assert observed["json"]["text"] == "Body"


def test_send_email_result_blocks_unverified_sender(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(email_utils.settings, "resend_sender", "Cordex Gym OS <noreply@cordex.com>")
    monkeypatch.setattr(email_utils, "_email_provider_block_reason", None)

    def fake_post(*_args, **_kwargs):
        return httpx.Response(403, json={"message": "The domain is not verified. Verify a domain before sending."})

    monkeypatch.setattr(email_utils.httpx, "post", fake_post)

    first = email_utils.send_email_result("member@example.com", "Subject", "Body")
    second = email_utils.send_email_result("member@example.com", "Subject", "Body")

    assert first.sent is False
    assert first.blocked is True
    assert first.reason == "sender_identity_unverified"
    assert second.sent is False
    assert second.blocked is True
    assert second.reason == "sender_identity_unverified"


def test_send_email_result_classifies_resend_permission_denied(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(email_utils.settings, "resend_sender", "Cordex Gym OS <onboarding@resend.dev>")
    monkeypatch.setattr(email_utils, "_email_provider_block_reason", None)

    def fake_post(*_args, **_kwargs):
        return httpx.Response(401, json={"message": "Invalid API key"})

    monkeypatch.setattr(email_utils.httpx, "post", fake_post)

    result = email_utils.send_email_result("member@example.com", "Subject", "Body")

    assert result.sent is False
    assert result.blocked is True
    assert result.reason == "resend_permission_denied"


def test_send_email_with_attachment_uses_base64_content(monkeypatch):
    observed = {}
    monkeypatch.setattr(email_utils.settings, "resend_api_key", "test-key")
    monkeypatch.setattr(email_utils.settings, "resend_sender", "Cordex Gym OS <onboarding@resend.dev>")
    monkeypatch.setattr(email_utils, "_email_provider_block_reason", None)

    def fake_post(_url, *, headers, json, timeout):
        observed.update({"json": json})
        return httpx.Response(200, json={"id": "email-123"})

    monkeypatch.setattr(email_utils.httpx, "post", fake_post)

    result = email_utils.send_email_with_attachment_result(
        "member@example.com",
        "Subject",
        "Body",
        filename="report.pdf",
        attachment_bytes=b"%PDF",
    )

    assert result.sent is True
    assert observed["json"]["attachments"] == [{"filename": "report.pdf", "content": "JVBERg=="}]
