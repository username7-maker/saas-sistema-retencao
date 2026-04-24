import httpx

from app.services import evolution_service


class _Response:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://evolution.example.com")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)


class _Client:
    def __init__(self, responses):
        self._responses = responses
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, *_args, **_kwargs):
        return self._responses.pop(0)

    def post(self, *_args, **_kwargs):
        self.posts.append(_kwargs.get("json"))
        return self._responses.pop(0)


def test_ensure_instance_reuses_existing_instance(monkeypatch):
    monkeypatch.setattr(
        evolution_service.httpx,
        "Client",
        lambda *args, **kwargs: _Client(
            [
                _Response(
                    200,
                    [{"name": "gym_1234567890abcdef1234567890abcdef"}],
                )
            ]
        ),
    )

    instance = evolution_service.ensure_instance("12345678-90ab-cdef-1234-567890abcdef")

    assert instance == "gym_1234567890abcdef1234567890abcdef"


def test_ensure_instance_falls_back_to_existing_after_create_error(monkeypatch):
    monkeypatch.setattr(
        evolution_service.httpx,
        "Client",
        lambda *args, **kwargs: _Client(
            [
                _Response(200, []),
                _Response(403, {"error": "forbidden"}),
                _Response(
                    200,
                    [{"instanceName": "gym_1234567890abcdef1234567890abcdef"}],
                ),
            ]
        ),
    )

    instance = evolution_service.ensure_instance("12345678-90ab-cdef-1234-567890abcdef")

    assert instance == "gym_1234567890abcdef1234567890abcdef"


def test_configure_webhook_uses_nested_payload(monkeypatch):
    client = _Client([_Response(201, {"ok": True})])
    monkeypatch.setattr(
        evolution_service.httpx,
        "Client",
        lambda *args, **kwargs: client,
    )

    configured = evolution_service.configure_webhook(
        "gym_1234567890abcdef1234567890abcdef",
        "https://api.example.com/api/v1/whatsapp/webhook",
        {"X-Webhook-Token": "token"},
    )

    assert configured is True
    assert client.posts == [
        {
            "webhook": {
                "enabled": True,
                "url": "https://api.example.com/api/v1/whatsapp/webhook",
                "headers": {"X-Webhook-Token": "token"},
                "byEvents": False,
                "base64": False,
                "events": [
                    "QRCODE_UPDATED",
                    "CONNECTION_UPDATE",
                    "STATUS_INSTANCE",
                    "MESSAGES_UPSERT",
                ],
            }
        }
    ]
