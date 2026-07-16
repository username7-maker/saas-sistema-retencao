def test_cors_preflight_allows_anthropometry_idempotency_header(client):
    response = client.options(
        "/api/v1/assessments/members/33333333-3333-3333-3333-333333333333/anthropometry",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()
