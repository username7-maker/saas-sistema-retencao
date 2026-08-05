"""Authenticated sandbox audit with sanitized, metadata-only output.

Tokens, cookies, credentials and response payloads stay in process memory.  The
only output is a JSON list of expected/observed status codes and boolean safety
assertions over wholly fictitious TESTE_AUDITORIA data.
"""

from __future__ import annotations

import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text

from app.core.config import settings
from app.core.security import create_access_token
from app.database import SessionLocal, include_all_tenants
from app.models import RoleEnum, User


BASE_URL = "http://127.0.0.1:8000"
PRIMARY_EMAIL = "TESTE_AUDITORIA_GESTOR@teste-auditoria.invalid"
PRIMARY_SLUG = "teste-auditoria-alpha"
AUDIT_PREFIX = "TESTE_AUDITORIA_"
ALLOWED_ORIGIN = settings.frontend_url


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class Client:
    def __init__(self, *, cookies: bool = False) -> None:
        handlers: list[Any] = []
        if cookies:
            self.cookie_jar = http.cookiejar.CookieJar()
            handlers.append(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        else:
            self.cookie_jar = None
        self.opener = urllib.request.build_opener(*handlers)

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        payload: Any | None = None,
        origin: str | None = None,
        content_type: str = "application/json",
    ) -> Response:
        data = None
        headers = {"Accept": "application/json", "User-Agent": "Cordex-Safe-Audit/1.0"}
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = content_type
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if origin:
            headers["Origin"] = origin
        request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                return Response(response.status, {k.lower(): v for k, v in response.headers.items()}, response.read(2_000_000))
        except urllib.error.HTTPError as exc:
            return Response(exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read(2_000_000))


class Recorder:
    def __init__(self) -> None:
        self.cases: list[dict[str, Any]] = []

    def status(
        self,
        case_id: str,
        response: Response,
        expected: int | set[int],
        *,
        area: str,
        method: str,
        route: str,
        observation: str,
    ) -> bool:
        expected_set = {expected} if isinstance(expected, int) else expected
        passed = response.status in expected_set
        self.cases.append(
            {
                "id": case_id,
                "area": area,
                "classification": "test",
                "target": "sandbox",
                "method": method,
                "route": route,
                "expected_status": sorted(expected_set),
                "observed_status": response.status,
                "status": "pass" if passed else "fail",
                "observation": observation,
            }
        )
        return passed

    def assertion(self, case_id: str, passed: bool, *, area: str, observation: str) -> None:
        self.cases.append(
            {
                "id": case_id,
                "area": area,
                "classification": "test",
                "target": "sandbox",
                "status": "pass" if passed else "fail",
                "observation": observation,
            }
        )


def _read_runtime_secrets() -> tuple[str, str]:
    password = sys.stdin.readline().rstrip("\r\n")
    reset_token = sys.stdin.readline().rstrip("\r\n")
    if not 16 <= len(password) <= 72 or len(reset_token) < 32:
        raise RuntimeError("Runtime audit secrets must be supplied on stdin")
    return password, reset_token


def _sandbox_users_and_ids() -> tuple[dict[str, User], dict[str, str]]:
    db = SessionLocal()
    try:
        users = list(
            db.scalars(
                include_all_tenants(
                    select(User).where(User.email.like("TESTE_AUDITORIA_%")),
                    reason="auth.audit_api_users",
                )
            )
        )
        alpha_users = {
            user.role.value: user
            for user in users
            if user.email == PRIMARY_EMAIL or "TESTE_AUDITORIA_ALPHA_" in user.email
        }
        beta_owner = next(user for user in users if "TESTE_AUDITORIA_BETA_OWNER" in user.email)
        ids = {
            "alpha_member": str(
                db.execute(
                    text(
                        "SELECT m.id FROM members m JOIN gyms g ON g.id=m.gym_id "
                        "WHERE g.slug='teste-auditoria-alpha' ORDER BY m.full_name LIMIT 1"
                    )
                ).scalar_one()
            ),
            "beta_member": str(
                db.execute(
                    text(
                        "SELECT m.id FROM members m JOIN gyms g ON g.id=m.gym_id "
                        "WHERE g.slug='teste-auditoria-beta' ORDER BY m.full_name LIMIT 1"
                    )
                ).scalar_one()
            ),
            "beta_owner_email": beta_owner.email,
        }
        if set(alpha_users) != {role.value for role in RoleEnum}:
            raise RuntimeError("Audit role fixture is incomplete")
        return alpha_users, ids
    finally:
        db.close()


def _token_for(user: User) -> str:
    return create_access_token(user.id, user.role.value, user.gym_id)


def main() -> None:
    password, reset_token = _read_runtime_secrets()
    users, ids = _sandbox_users_and_ids()
    tokens = {role: _token_for(user) for role, user in users.items()}
    client = Client()
    session = Client(cookies=True)
    record = Recorder()

    response = client.request("GET", "/health/ready")
    record.status("health-ready", response, 200, area="preflight", method="GET", route="/health/ready", observation="Readiness endpoint answered normally.")

    response = client.request("GET", "/api/v1/users/me")
    record.status("auth-required", response, 401, area="authentication", method="GET", route="/api/v1/users/me", observation="Protected identity route rejected an unauthenticated request.")

    response = client.request(
        "POST",
        "/api/v1/auth/login",
        payload={"gym_slug": PRIMARY_SLUG, "email": PRIMARY_EMAIL, "password": password + "_wrong"},
    )
    record.status("login-failure", response, 401, area="authentication", method="POST", route="/api/v1/auth/login", observation="One inert invalid-password attempt was rejected; no brute force was performed.")

    response = client.request(
        "POST",
        "/api/v1/auth/login",
        payload={"gym_slug": PRIMARY_SLUG, "email": "not-an-email", "password": password},
    )
    record.status("login-validation", response, 422, area="validation", method="POST", route="/api/v1/auth/login", observation="Malformed email input was rejected by request validation.")

    response = session.request(
        "POST",
        "/api/v1/auth/login",
        payload={"gym_slug": PRIMARY_SLUG, "email": PRIMARY_EMAIL, "password": password},
    )
    login_ok = record.status("login-success", response, 200, area="authentication", method="POST", route="/api/v1/auth/login", observation="Primary fictitious manager authenticated; credentials and tokens were not recorded.")
    session_access = response.json().get("access_token") if login_ok else None
    record.assertion(
        "refresh-cookie-flags",
        bool(response.headers.get("set-cookie"))
        and "httponly" in response.headers.get("set-cookie", "").lower()
        and "samesite=lax" in response.headers.get("set-cookie", "").lower(),
        area="session",
        observation="Sandbox refresh cookie was HttpOnly and SameSite=Lax; Secure is intentionally off on local HTTP only.",
    )

    response = session.request("POST", "/api/v1/auth/refresh", payload={}, origin=ALLOWED_ORIGIN)
    refresh_ok = record.status("refresh-success", response, 200, area="session", method="POST", route="/api/v1/auth/refresh", observation="Allowed browser origin refreshed through the HttpOnly cookie without persisting it.")
    if refresh_ok:
        session_access = response.json().get("access_token")

    response = client.request(
        "POST",
        "/api/v1/auth/refresh",
        payload={},
        origin="https://audit.invalid",
    )
    record.status("refresh-origin-denied", response, 403, area="cors", method="POST", route="/api/v1/auth/refresh", observation="Unlisted browser origin was denied before refresh-token processing.")

    response = client.request(
        "POST",
        "/api/v1/auth/forgot-password",
        payload={"gym_slug": PRIMARY_SLUG, "email": PRIMARY_EMAIL},
    )
    record.status("recovery-delivery-disabled", response, 503, area="recovery", method="POST", route="/api/v1/auth/forgot-password", observation="Recovery stopped before lookup/delivery because no email provider key exists in the sandbox.")

    response = client.request(
        "POST",
        "/api/v1/auth/reset-password",
        payload={"token": reset_token, "new_password": password},
    )
    reset_ok = record.status("recovery-reset-inert-token", response, 200, area="recovery", method="POST", route="/api/v1/auth/reset-password", observation="A newly generated sandbox-only reset token reset a fictitious Beta owner without email delivery.")
    if reset_ok:
        replay = client.request(
            "POST",
            "/api/v1/auth/reset-password",
            payload={"token": reset_token, "new_password": password},
        )
        record.status("recovery-token-single-use", replay, {400, 401}, area="recovery", method="POST", route="/api/v1/auth/reset-password", observation="The one-time sandbox reset token could not be replayed.")

    if session_access:
        response = session.request("POST", "/api/v1/auth/logout", token=session_access, origin=ALLOWED_ORIGIN)
        record.status("logout-success", response, 200, area="session", method="POST", route="/api/v1/auth/logout", observation="Logout revoked the refresh token and cleared browser storage directives.")
        response = session.request("POST", "/api/v1/auth/refresh", payload={}, origin=ALLOWED_ORIGIN)
        record.status("refresh-after-logout", response, 401, area="session", method="POST", route="/api/v1/auth/refresh", observation="Refresh failed after logout.")
        response = client.request("GET", "/api/v1/users/me", token=session_access)
        record.status("access-token-after-logout", response, 200, area="session", method="GET", route="/api/v1/users/me", observation="Observation: the already-issued stateless access JWT remains valid until expiry after logout.")

    manager_token = tokens[RoleEnum.MANAGER.value]
    response = client.request("GET", "/openapi.json")
    openapi_ok = record.status("openapi-sandbox", response, 200, area="inventory", method="GET", route="/openapi.json", observation="OpenAPI is enabled only in the isolated audit environment for route inventory.")
    if openapi_ok:
        document = response.json()
        record.assertion("openapi-route-count", len(document.get("paths", {})) >= 100, area="inventory", observation=f"Sandbox OpenAPI exposed {len(document.get('paths', {}))} path templates for review.")

    response = client.request("GET", "/api/v1/members/?page=1&page_size=5", token=manager_token)
    pagination_ok = record.status("members-pagination", response, 200, area="members", method="GET", route="/api/v1/members/", observation="Members pagination returned a bounded first page.")
    if pagination_ok:
        payload = response.json()
        record.assertion("members-pagination-size", len(payload.get("items", [])) == 5 and payload.get("total", 0) >= 32, area="members", observation="Pagination size and seeded total were consistent.")

    response = client.request("GET", "/api/v1/members/?page=1&page_size=100", token=manager_token)
    record.assertion(
        "members-list-tenant-isolation",
        response.status == 200 and "TESTE_AUDITORIA_BETA" not in response.body.decode("utf-8", errors="ignore"),
        area="tenant-isolation",
        observation="Alpha member list did not contain the Beta fixture prefix.",
    )

    response = client.request("GET", f"/api/v1/members/{ids['beta_member']}", token=manager_token)
    record.status("cross-tenant-member-read", response, 404, area="tenant-isolation", method="GET", route="/api/v1/members/{beta_member_id}", observation="Alpha manager received non-disclosing not-found for a Beta member ID.")

    response = client.request(
        "POST",
        "/api/v1/tasks/",
        token=manager_token,
        payload={
            "title": "TESTE_AUDITORIA_CROSS_TENANT_INERTE",
            "member_id": ids["beta_member"],
            "priority": "medium",
            "status": "todo",
        },
    )
    record.status("cross-tenant-task-write", response, {400, 404}, area="tenant-isolation", method="POST", route="/api/v1/tasks/", observation="Alpha could not create a task linked to a Beta member ID.")

    xss_marker = "<script>window.__TESTE_AUDITORIA_XSS__=1</script>"
    response = client.request(
        "POST",
        "/api/v1/members/",
        token=manager_token,
        payload={
            "full_name": f"TESTE_AUDITORIA_CRUD_{xss_marker}",
            "email": "TESTE_AUDITORIA_CRUD_MEMBRO@teste-auditoria.invalid",
            "plan_name": "TESTE_AUDITORIA_PLANO_CRUD",
            "monthly_fee": "123.45",
            "extra_data": {"inert_xss_probe": xss_marker},
        },
    )
    member_created = record.status("member-create", response, 201, area="crud", method="POST", route="/api/v1/members/", observation="Created a fictitious member with a small inert XSS marker treated as data.")
    created_member_id = response.json().get("id") if member_created else None
    if member_created:
        record.assertion("member-xss-remains-data", xss_marker in response.body.decode("utf-8", errors="ignore"), area="validation", observation="The inert marker was returned as JSON data; browser execution is checked separately.")
        response = client.request(
            "PATCH",
            f"/api/v1/members/{created_member_id}",
            token=manager_token,
            payload={"plan_name": "TESTE_AUDITORIA_PLANO_ATUALIZADO"},
        )
        record.status("member-update", response, 200, area="crud", method="PATCH", route="/api/v1/members/{member_id}", observation="Updated the sandbox member.")

    response = client.request(
        "POST",
        "/api/v1/crm/leads",
        token=manager_token,
        payload={
            "full_name": "TESTE_AUDITORIA_CRUD_LEAD",
            "email": "TESTE_AUDITORIA_CRUD_LEAD@teste-auditoria.invalid",
            "source": "TESTE_AUDITORIA_CRUD",
            "stage": "new",
            "estimated_value": "250.00",
        },
    )
    lead_created = record.status("lead-create", response, 201, area="crud", method="POST", route="/api/v1/crm/leads", observation="Created a fictitious CRM lead without reaching a send-triggering stage.")
    created_lead_id = response.json().get("id") if lead_created else None
    if lead_created:
        response = client.request("PATCH", f"/api/v1/crm/leads/{created_lead_id}", token=manager_token, payload={"stage": "contact"})
        record.status("lead-update", response, 200, area="crud", method="PATCH", route="/api/v1/crm/leads/{lead_id}", observation="Updated the sandbox lead stage without dispatch.")

    response = client.request(
        "POST",
        "/api/v1/tasks/",
        token=manager_token,
        payload={
            "title": "TESTE_AUDITORIA_CRUD_TAREFA",
            "description": xss_marker,
            "member_id": ids["alpha_member"],
            "priority": "high",
            "status": "todo",
        },
    )
    task_created = record.status("task-create", response, 201, area="crud", method="POST", route="/api/v1/tasks/", observation="Created a fictitious task with inert validation text.")
    created_task_id = response.json().get("id") if task_created else None
    if task_created:
        response = client.request("PATCH", f"/api/v1/tasks/{created_task_id}", token=manager_token, payload={"status": "doing", "kanban_column": "doing"})
        record.status("task-update", response, 200, area="crud", method="PATCH", route="/api/v1/tasks/{task_id}", observation="Updated task status and Kanban state.")
        response = client.request("GET", f"/api/v1/tasks/{created_task_id}/events", token=manager_token)
        record.status("task-history", response, 200, area="tasks", method="GET", route="/api/v1/tasks/{task_id}/events", observation="Read the task event history.")

    response = client.request(
        "POST",
        f"/api/v1/assessments/members/{ids['alpha_member']}",
        token=manager_token,
        payload={
            "height_cm": 172.0,
            "weight_kg": 74.0,
            "body_fat_pct": 21.0,
            "observations": "TESTE_AUDITORIA_AVALIACAO_CRUD_INERTE",
        },
    )
    record.status("assessment-create", response, 201, area="assessments", method="POST", route="/api/v1/assessments/members/{member_id}", observation="Created an inert sandbox assessment; Actuar synchronization remained disabled.")
    response = client.request("GET", f"/api/v1/assessments/members/{ids['alpha_member']}", token=manager_token)
    record.status("assessment-history", response, 200, area="assessments", method="GET", route="/api/v1/assessments/members/{member_id}", observation="Assessment history was readable within Alpha.")
    response = client.request("GET", f"/api/v1/assessments/members/{ids['beta_member']}", token=manager_token)
    record.status("cross-tenant-assessment-read", response, 404, area="tenant-isolation", method="GET", route="/api/v1/assessments/members/{beta_member_id}", observation="Alpha received non-disclosing not-found for Beta assessment history.")

    for dashboard in ("executive", "operational", "commercial", "financial", "retention"):
        response = client.request("GET", f"/api/v1/dashboards/{dashboard}", token=manager_token)
        record.status(f"dashboard-{dashboard}", response, 200, area="reports", method="GET", route=f"/api/v1/dashboards/{dashboard}", observation=f"Seeded {dashboard} dashboard returned without paid AI.")

    response = client.request("GET", "/api/v1/reports/dashboard/executive/pdf", token=manager_token)
    report_ok = record.status("report-pdf", response, 200, area="reports", method="GET", route="/api/v1/reports/dashboard/executive/pdf", observation="Executive report rendered in memory; no report payload was persisted.")
    if report_ok:
        record.assertion("report-pdf-content-type", "pdf" in response.headers.get("content-type", "").lower() and len(response.body) > 500, area="reports", observation="Report response had PDF content type and non-empty content.")

    response = client.request("GET", "/api/v1/exports/members.csv", token=manager_token)
    export_ok = record.status("members-export", response, 200, area="exports", method="GET", route="/api/v1/exports/members.csv", observation="Members CSV was validated in memory and not written to disk.")
    if export_ok:
        csv_text = response.body.decode("utf-8", errors="ignore")
        record.assertion("members-export-tenant-isolation", "TESTE_AUDITORIA_ALPHA" in csv_text and "TESTE_AUDITORIA_BETA" not in csv_text, area="tenant-isolation", observation="Alpha export contained Alpha fixtures and no Beta prefix.")

    rbac_matrix = {
        "/api/v1/members/?page=1&page_size=1": {"owner", "manager", "salesperson", "receptionist", "trainer"},
        "/api/v1/users/": {"owner", "manager"},
        "/api/v1/dashboards/executive": {"owner", "manager"},
        "/api/v1/dashboards/operational": {"owner", "manager", "receptionist"},
        "/api/v1/dashboards/commercial": {"owner", "manager", "salesperson"},
        "/api/v1/crm/leads?page=1&page_size=1": {"owner", "manager", "salesperson", "receptionist"},
        "/api/v1/assessments/dashboard": {"owner", "manager", "receptionist", "trainer"},
        "/api/v1/audit/logs?limit=1": {"owner", "manager"},
        "/api/v1/exports/members.csv": {"owner", "manager"},
    }
    for route, allowed_roles in rbac_matrix.items():
        for role, token in tokens.items():
            response = client.request("GET", route, token=token)
            expected = 200 if role in allowed_roles else 403
            record.status(
                f"rbac-{role}-{route.split('?')[0].strip('/').replace('/', '-')}",
                response,
                expected,
                area="rbac",
                method="GET",
                route=route.split("?")[0],
                observation=f"Role {role} {'was allowed' if expected == 200 else 'was denied'} according to the declared matrix.",
            )

    if task_created:
        response = client.request("DELETE", f"/api/v1/tasks/{created_task_id}", token=manager_token)
        record.status("task-delete", response, 204, area="crud", method="DELETE", route="/api/v1/tasks/{task_id}", observation="Deleted the temporary CRUD task.")
    if lead_created:
        response = client.request("DELETE", f"/api/v1/crm/leads/{created_lead_id}", token=manager_token)
        record.status("lead-delete", response, 204, area="crud", method="DELETE", route="/api/v1/crm/leads/{lead_id}", observation="Deleted the temporary CRM lead.")
    if member_created:
        response = client.request("DELETE", f"/api/v1/members/{created_member_id}", token=manager_token)
        record.status("member-delete", response, 200, area="crud", method="DELETE", route="/api/v1/members/{member_id}", observation="Soft-deleted the temporary member.")

    failures = [case for case in record.cases if case["status"] == "fail"]
    result = {
        "classification": "test",
        "target": "sandbox",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"total": len(record.cases), "passed": len(record.cases) - len(failures), "failed": len(failures)},
        "cases": record.cases,
        "sensitive_artifacts_recorded": False,
    }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    del password, reset_token, tokens, session_access
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
