from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import Response

from tests.conftest import GYM_ID


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/api/v1/dashboards/executive",
        "raw_path": b"/api/v1/dashboards/executive",
        "query_string": b"",
        "headers": [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_tenant_context_middleware_sets_gym_from_bearer_token():
    from app.main import tenant_context_middleware

    request = _request_with_headers({"Authorization": "Bearer valid-token"})

    async def call_next(_request: Request) -> Response:
        return Response("ok", status_code=200)

    with patch("app.main.decode_token", return_value={"gym_id": str(GYM_ID)}), patch(
        "app.main.set_current_gym_id"
    ) as set_current_gym_id, patch("app.main.clear_current_gym_id") as clear_current_gym_id:
        response = __import__("asyncio").run(tenant_context_middleware(request, call_next))

    assert response.status_code == 200
    set_current_gym_id.assert_called_once_with(GYM_ID)
    assert clear_current_gym_id.call_count == 2


def test_tenant_context_middleware_ignores_invalid_token():
    from app.main import tenant_context_middleware

    request = _request_with_headers({"Authorization": "Bearer invalid-token"})

    async def call_next(_request: Request) -> Response:
        return Response("ok", status_code=200)

    with patch("app.main.decode_token", side_effect=ValueError("invalid")), patch(
        "app.main.set_current_gym_id"
    ) as set_current_gym_id, patch("app.main.clear_current_gym_id") as clear_current_gym_id:
        response = __import__("asyncio").run(tenant_context_middleware(request, call_next))

    assert response.status_code == 200
    set_current_gym_id.assert_not_called()
    assert clear_current_gym_id.call_count >= 2
