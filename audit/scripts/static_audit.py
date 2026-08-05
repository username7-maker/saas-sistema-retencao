"""Deterministic, secret-safe static inventory for the Cordex audit report."""

from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path


EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "coverage",
    "playwright-report",
    "test-results",
    "data",
    ".planning",
    ".impeccable",
    "everything-claude-code",
}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".yml", ".yaml", ".toml", ".md"}


def _safe_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            continue
        yield path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _line_for(text: str, needle: str) -> int:
    index = text.find(needle)
    return 1 if index < 0 else text[:index].count("\n") + 1


def _tenant_guard_inventory(root: Path) -> tuple[list[str], list[str]]:
    model_dir = root / "saas-backend" / "app" / "models"
    tenant_models: set[str] = set()
    for path in model_dir.glob("*.py"):
        try:
            tree = ast.parse(_read(path))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if any(isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == "gym_id" for item in node.body):
                tenant_models.add(node.name)

    database_text = _read(root / "saas-backend" / "app" / "database.py")
    match = re.search(r"TENANT_SCOPED_MODELS\s*=\s*\((.*?)\n\)", database_text, re.DOTALL)
    scoped = set(re.findall(r"^\s*([A-Z][A-Za-z0-9_]*)\s*,?\s*$", match.group(1), re.MULTILINE)) if match else set()
    return sorted(tenant_models), sorted(tenant_models - scoped)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo.resolve()

    tenant_models, missing_tenant_models = _tenant_guard_inventory(root)
    findings: list[dict] = []

    database_path = root / "saas-backend" / "app" / "database.py"
    if missing_tenant_models:
        findings.append(
            {
                "id": "STATIC-TENANT-BACKSTOP",
                "severity": "high",
                "classification": "observation",
                "title": "Tenant-scoped models missing from the default-deny loader backstop",
                "location": f"saas-backend/app/database.py:{_line_for(_read(database_path), 'TENANT_SCOPED_MODELS')}",
                "evidence": {"tenant_models": len(tenant_models), "missing_models": missing_tenant_models},
                "impact": "Those models depend entirely on endpoint/service predicates for read isolation.",
                "remediation": "Add every gym_id model to the backstop and enforce mapper parity with a regression test.",
            }
        )

    kommo_path = root / "saas-backend" / "app" / "services" / "kommo_service.py"
    kommo_text = _read(kommo_path)
    if "def find_member_link_by_kommo_ids" in kommo_text and "KommoMemberLink.updated_at.desc()" in kommo_text:
        findings.append(
            {
                "id": "STATIC-KOMMO-TENANT-ROUTING",
                "severity": "high",
                "classification": "inference",
                "title": "Kommo inbound link resolution is not qualified by tenant/account",
                "location": f"saas-backend/app/services/kommo_service.py:{_line_for(kommo_text, 'def find_member_link_by_kommo_ids')}",
                "evidence": "The cross-tenant lookup resolves reused external lead/contact IDs by most recently updated link.",
                "impact": "If separate Kommo accounts reuse IDs, an inbound event can be assigned to the wrong tenant.",
                "remediation": "Include account/base URL or tenant identity in the lookup key and webhook authentication context.",
            }
        )

    reset_path = root / "saas-frontend" / "src" / "pages" / "auth" / "ResetPasswordPage.tsx"
    reset_text = _read(reset_path)
    query_token_needle = 'queryParams.get("token")'
    if query_token_needle in reset_text:
        findings.append(
            {
                "id": "STATIC-RESET-TOKEN-QUERY",
                "severity": "medium",
                "classification": "observation",
                "title": "Password reset token accepts a query-string fallback",
                "location": f"saas-frontend/src/pages/auth/ResetPasswordPage.tsx:{_line_for(reset_text, query_token_needle)}",
                "impact": "Query tokens can enter browser history, server logs and referrer data despite the UI's fragment-only safety claim.",
                "remediation": "Accept the token only from the URL fragment, remove it immediately, and never render it visibly.",
            }
        )
    if 'type="text"' in reset_text and "token" in reset_text:
        findings.append(
            {
                "id": "STATIC-RESET-TOKEN-VISIBLE",
                "severity": "medium",
                "classification": "observation",
                "title": "Password reset token is rendered in a visible text input",
                "location": f"saas-frontend/src/pages/auth/ResetPasswordPage.tsx:{_line_for(reset_text, 'type=\"text\"')}",
                "impact": "The token can be exposed visually or captured by screenshots and assistive tooling.",
                "remediation": "Keep it only in component memory and remove the visible field.",
            }
        )

    ui_checks = [
        ("FormField.tsx", "htmlFor", "STATIC-A11Y-FORM-LABEL", "FormField labels are not programmatically associated", "medium"),
        ("Tabs.tsx", 'role="tablist"', "STATIC-A11Y-TABS", "Tabs omit tablist/tab/tabpanel semantics and keyboard model", "medium"),
        ("Drawer.tsx", 'role="dialog"', "STATIC-A11Y-DRAWER", "Drawer omits modal semantics and focus containment", "medium"),
    ]
    ui_dir = root / "saas-frontend" / "src" / "components" / "ui2"
    for filename, required, finding_id, title, severity in ui_checks:
        source = _read(ui_dir / filename)
        if required not in source:
            findings.append(
                {
                    "id": finding_id,
                    "severity": severity,
                    "classification": "observation",
                    "title": title,
                    "location": f"saas-frontend/src/components/ui2/{filename}:1",
                    "impact": "Keyboard and assistive-technology users receive incomplete names, roles, states or focus behavior.",
                    "remediation": "Implement the corresponding WAI-ARIA pattern and cover it with keyboard-focused tests.",
                }
            )

    auth_context_path = root / "saas-frontend" / "src" / "contexts" / "AuthContext.tsx"
    auth_context_text = _read(auth_context_path)
    has_cross_tab_signal = (
        "BroadcastChannel" in auth_context_text
        or 'addEventListener("storage"' in auth_context_text
        or "addEventListener('storage'" in auth_context_text
        or "onstorage" in auth_context_text
    )
    if not has_cross_tab_signal:
        findings.append(
            {
                "id": "STATIC-MULTITAB-LOGOUT",
                "severity": "medium",
                "classification": "inference",
                "title": "Logout has no cross-tab propagation mechanism",
                "location": f"saas-frontend/src/contexts/AuthContext.tsx:{_line_for(auth_context_text, 'const logout')}",
                "impact": "Other open tabs can retain an in-memory access JWT until it expires or a request is rejected.",
                "remediation": "Broadcast logout/session-version changes across tabs and consider server-side access-token revocation/versioning.",
            }
        )

    dockerignore_checks = {
        "backend": root / "saas-backend" / ".dockerignore",
        "frontend": root / "saas-frontend" / ".dockerignore",
    }
    dockerignore_safe = {
        name: path.exists() and ".env" in _read(path) and "node_modules" in _read(path) if name == "frontend" else path.exists() and ".env" in _read(path)
        for name, path in dockerignore_checks.items()
    }

    route_text = _read(root / "saas-frontend" / "src" / "App.tsx")
    frontend_routes = sorted(set(re.findall(r'path="([^"*]+|\*)"', route_text)))
    backend_operations = 0
    backend_router_files = 0
    for router_path in (root / "saas-backend" / "app" / "routers").glob("*.py"):
        count = len(re.findall(r"@router\.(?:get|post|put|patch|delete)\(", _read(router_path)))
        if count:
            backend_router_files += 1
            backend_operations += count

    secret_patterns = {
        "private_key_header": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    }
    secret_hits: dict[str, list[str]] = {name: [] for name in secret_patterns}
    scanned_files = 0
    for path in _safe_files(root):
        scanned_files += 1
        content = _read(path)
        rel = path.relative_to(root).as_posix()
        for name, pattern in secret_patterns.items():
            if pattern.search(content):
                secret_hits[name].append(rel)

    output = {
        "classification": "observation",
        "target": "workspace-current",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inventory": {
            "frontend_routes": frontend_routes,
            "frontend_route_count": len(frontend_routes),
            "backend_router_files": backend_router_files,
            "backend_operations": backend_operations,
            "tenant_models": len(tenant_models),
            "dockerignore_excludes_local_env": dockerignore_safe,
        },
        "secret_scan": {
            "scope": "source text excluding env files, dependencies, build artifacts, planning and evidence",
            "scanned_files": scanned_files,
            "hits_by_rule": {name: sorted(paths) for name, paths in secret_hits.items()},
            "values_recorded": False,
        },
        "findings": findings,
    }
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
