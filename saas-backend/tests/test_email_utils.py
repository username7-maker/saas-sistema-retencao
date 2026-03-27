from python_http_client.exceptions import HTTPError

from app.utils import email as email_utils


def test_send_email_result_is_blocked_without_api_key(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "sendgrid_api_key", "")
    monkeypatch.setattr(email_utils, "_sendgrid_block_reason", None)

    result = email_utils.send_email_result("member@example.com", "Subject", "Body")

    assert result.sent is False
    assert result.blocked is True
    assert result.reason == "sendgrid_api_key_missing"


def test_send_email_result_blocks_unverified_sender(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "sendgrid_api_key", "test-key")
    monkeypatch.setattr(email_utils.settings, "sendgrid_sender", "owner@example.com")
    monkeypatch.setattr(email_utils, "_sendgrid_block_reason", None)

    class FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def send(self, _message):
            raise HTTPError(
                403,
                "Forbidden",
                b'{"errors":[{"message":"The from address does not match a verified Sender Identity."}]}',
                {},
            )

    monkeypatch.setattr(email_utils, "SendGridAPIClient", FakeClient)

    first = email_utils.send_email_result("member@example.com", "Subject", "Body")
    second = email_utils.send_email_result("member@example.com", "Subject", "Body")

    assert first.sent is False
    assert first.blocked is True
    assert first.reason == "sender_identity_unverified"
    assert second.sent is False
    assert second.blocked is True
    assert second.reason == "sender_identity_unverified"
