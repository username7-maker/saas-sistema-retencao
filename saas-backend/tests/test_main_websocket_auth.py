from app.main import _extract_websocket_auth_token


def test_extract_websocket_auth_token_returns_token_for_valid_auth_message():
    token = _extract_websocket_auth_token('{"type":"auth","token":"jwt-token"}')
    assert token == "jwt-token"


def test_extract_websocket_auth_token_rejects_non_auth_messages():
    token = _extract_websocket_auth_token('{"type":"ping","token":"jwt-token"}')
    assert token is None


def test_extract_websocket_auth_token_rejects_invalid_json():
    token = _extract_websocket_auth_token("not-json")
    assert token is None
