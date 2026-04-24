#!/usr/bin/env python
"""Smoke test for the AI Gym OS pilot environment.

Required environment variables:
  PILOT_API_BASE_URL
  PILOT_GYM_SLUG
  PILOT_LOGIN_EMAIL
  PILOT_LOGIN_PASSWORD

Optional:
  PILOT_FRONTEND_URL
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


REQUIRED_ENV = (
    "PILOT_API_BASE_URL",
    "PILOT_GYM_SLUG",
    "PILOT_LOGIN_EMAIL",
    "PILOT_LOGIN_PASSWORD",
)


@dataclass
class SmokeContext:
    api_base_url: str
    gym_slug: str
    email: str
    password: str
    frontend_url: str | None
    access_token: str | None = None


class SmokeFailure(RuntimeError):
    pass


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SmokeFailure(f"Variavel obrigatoria ausente: {name}")
    return value


def _load_context() -> SmokeContext:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name, "").strip()]
    if missing:
        raise SmokeFailure(f"Variaveis obrigatorias ausentes: {', '.join(missing)}")

    return SmokeContext(
        api_base_url=_env("PILOT_API_BASE_URL").rstrip("/"),
        gym_slug=_env("PILOT_GYM_SLUG"),
        email=_env("PILOT_LOGIN_EMAIL"),
        password=_env("PILOT_LOGIN_PASSWORD"),
        frontend_url=os.getenv("PILOT_FRONTEND_URL", "").strip() or None,
    )


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            data = _decode_json(raw)
            return response.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        data = _decode_json(raw)
        raise SmokeFailure(f"{method} {url} retornou HTTP {exc.code}: {data}") from exc
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"{method} {url} falhou: {exc.reason}") from exc


def _decode_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")[:500]


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def _step(name: str, fn) -> None:
    started = time.perf_counter()
    print(f"[smoke] {name}...", flush=True)
    fn()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    print(f"[smoke] OK {name} ({elapsed_ms}ms)", flush=True)


def _get_api(ctx: SmokeContext, path: str) -> Any:
    status_code, data = _request("GET", f"{ctx.api_base_url}{path}", token=ctx.access_token)
    _expect(200 <= status_code < 300, f"GET {path} retornou status inesperado: {status_code}")
    return data


def _assert_paginated(data: Any, label: str) -> None:
    _expect(isinstance(data, dict), f"{label} deveria retornar objeto paginado")
    _expect(isinstance(data.get("items"), list), f"{label} nao retornou lista items")
    _expect(isinstance(data.get("total"), int), f"{label} nao retornou total int")


def run_smoke(ctx: SmokeContext) -> None:
    def health() -> None:
        status_code, data = _request("GET", f"{ctx.api_base_url}/health")
        _expect(status_code == 200, "/health deveria retornar 200")
        _expect(isinstance(data, dict) and data.get("status") == "ok", "/health sem status ok")

    def readiness() -> None:
        status_code, data = _request("GET", f"{ctx.api_base_url}/health/ready")
        _expect(status_code == 200, "/health/ready deveria retornar 200")
        _expect(isinstance(data, dict) and data.get("status") == "ok", "/health/ready sem status ok")

    def login() -> None:
        status_code, data = _request(
            "POST",
            f"{ctx.api_base_url}/api/v1/auth/login",
            payload={"gym_slug": ctx.gym_slug, "email": ctx.email, "password": ctx.password},
        )
        _expect(status_code == 200, "login deveria retornar 200")
        _expect(isinstance(data, dict) and data.get("access_token"), "login nao retornou access_token")
        ctx.access_token = str(data["access_token"])

    def current_user() -> None:
        data = _get_api(ctx, "/api/v1/users/me")
        _expect(isinstance(data, dict) and data.get("gym_id"), "/users/me sem gym_id")
        _expect(data.get("email") == ctx.email, "/users/me retornou usuario diferente do login")

    def core_reads() -> None:
        for path in (
            "/api/v1/dashboards/executive",
            "/api/v1/dashboards/retention",
            "/api/v1/dashboards/operational",
            "/api/v1/assessments/dashboard",
        ):
            data = _get_api(ctx, path)
            _expect(isinstance(data, dict), f"{path} deveria retornar objeto")

        for path, label in (
            ("/api/v1/members/?page=1&page_size=5", "members"),
            ("/api/v1/crm/leads?page=1&page_size=5", "crm leads"),
            ("/api/v1/tasks/?page=1&page_size=5", "tasks"),
            ("/api/v1/notifications/?page=1&page_size=5", "notifications"),
        ):
            _assert_paginated(_get_api(ctx, path), label)

    def frontend() -> None:
        if not ctx.frontend_url:
            print("[smoke] SKIP frontend: PILOT_FRONTEND_URL nao definido", flush=True)
            return
        status_code, _data = _request("GET", ctx.frontend_url.rstrip("/"), timeout=20)
        _expect(status_code == 200, "frontend deveria retornar 200")

    for name, fn in (
        ("API liveness", health),
        ("API readiness", readiness),
        ("login", login),
        ("usuario atual", current_user),
        ("leituras operacionais", core_reads),
        ("frontend", frontend),
    ):
        _step(name, fn)


def main() -> int:
    try:
        ctx = _load_context()
        run_smoke(ctx)
    except SmokeFailure as exc:
        print(f"[smoke] FAIL {exc}", file=sys.stderr)
        return 1

    print("[smoke] PILOTO_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
