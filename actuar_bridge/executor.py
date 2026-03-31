from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


ACTUAR_SELECTORS = {
    "member_search_input": 'input[name="search"], input[name="member_search"], input[placeholder*="Aluno"], input[placeholder*="Buscar"]',
    "member_search_submit": 'button:has-text("Buscar"), button:has-text("Pesquisar"), button[type="submit"]',
    "member_result_row": '[data-testid="member-result"], table tbody tr, .member-row',
    "member_result_open": 'a, button',
    "body_composition_tab": 'a:has-text("Bioimped"), a:has-text("Compos"), button:has-text("Bioimped"), button:has-text("Compos")',
    "body_composition_form": 'form, [data-testid="body-composition-form"]',
    "save_button": 'button:has-text("Salvar"), button[type="submit"], input[type="submit"]',
}

ACTUAR_FIELD_SELECTORS = {
    "evaluation_date": 'input[name="evaluation_date"], input[name="date"], input[type="date"]',
    "weight": 'input[name="weight"], input[name="weight_kg"]',
    "body_fat_percent": 'input[name="body_fat_percent"], input[name="fat_pct"], input[name="bodyFat"]',
    "lean_mass_kg": 'input[name="lean_mass_kg"], input[name="fat_free_mass_kg"]',
    "muscle_mass_kg": 'input[name="muscle_mass_kg"], input[name="skeletal_muscle_kg"]',
    "bmi": 'input[name="bmi"]',
    "body_water_percent": 'input[name="body_water_percent"], input[name="water_pct"]',
    "notes": 'textarea[name="notes"], textarea',
}


@dataclass(slots=True)
class BridgeExecutionResult:
    succeeded: bool
    external_id: str | None = None
    action_log: list[dict[str, Any]] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    manual_fallback: bool = True


class BridgeExecutor(Protocol):
    def execute(self, job: dict[str, Any]) -> BridgeExecutionResult:
        ...


class DryRunBridgeExecutor:
    def execute(self, job: dict[str, Any]) -> BridgeExecutionResult:
        return BridgeExecutionResult(
            succeeded=True,
            external_id=job.get("actuar_external_id"),
            action_log=[{"event": "dry_run_completed", "job_id": job.get("job_id")}],
        )


class AttachedActuarBrowserExecutor:
    def __init__(
        self,
        *,
        debug_url: str = "http://127.0.0.1:9222",
        page_url_hint: str = "actuar",
        timeout_ms: int = 15000,
    ) -> None:
        self.debug_url = debug_url.rstrip("/")
        self.page_url_hint = page_url_hint.lower()
        self.timeout_ms = timeout_ms

    def execute(self, job: dict[str, Any]) -> BridgeExecutionResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - exercised only where playwright exists
            return BridgeExecutionResult(
                succeeded=False,
                error_code="playwright_unavailable",
                error_message=str(exc),
                retryable=False,
                manual_fallback=True,
            )

        with sync_playwright() as playwright:  # pragma: no cover - not exercised in CI
            browser = playwright.chromium.connect_over_cdp(self.debug_url)
            page = self._find_actuar_page(browser)
            if page is None:
                return BridgeExecutionResult(
                    succeeded=False,
                    error_code="actuar_tab_not_found",
                    error_message="Nenhuma aba aberta do Actuar foi encontrada no navegador local.",
                    retryable=False,
                    manual_fallback=True,
                )
            page.set_default_timeout(self.timeout_ms)
            member_context = self._locate_member(page, job)
            if not member_context["ok"]:
                return BridgeExecutionResult(
                    succeeded=False,
                    error_code=member_context["error_code"],
                    error_message=member_context["error_message"],
                    retryable=False,
                    manual_fallback=True,
                )
            page.locator(ACTUAR_SELECTORS["body_composition_tab"]).first.click()
            page.wait_for_load_state("networkidle")
            form = page.locator(ACTUAR_SELECTORS["body_composition_form"]).first
            if form.count() == 0:
                return BridgeExecutionResult(
                    succeeded=False,
                    error_code="actuar_form_changed",
                    error_message="Formulario de bioimpedancia do Actuar nao foi encontrado na aba aberta.",
                    retryable=False,
                    manual_fallback=True,
                )
            action_log = self._fill_form(page, job)
            page.locator(ACTUAR_SELECTORS["save_button"]).first.click()
            page.wait_for_load_state("networkidle")
            return BridgeExecutionResult(
                succeeded=True,
                external_id=job.get("actuar_external_id") or member_context.get("external_id"),
                action_log=action_log,
            )

    def _find_actuar_page(self, browser) -> Any | None:
        for context in browser.contexts:
            for page in context.pages:
                if self.page_url_hint in (page.url or "").lower():
                    return page
        return None

    def _locate_member(self, page, job: dict[str, Any]) -> dict[str, Any]:
        search_value = job.get("actuar_external_id") or _normalize_document(job.get("member_document")) or job.get("member_name")
        if not search_value:
            return {"ok": False, "error_code": "member_context_missing", "error_message": "Sem contexto suficiente para localizar o aluno no Actuar."}
        search_input = page.locator(ACTUAR_SELECTORS["member_search_input"]).first
        if search_input.count() == 0:
            return {"ok": False, "error_code": "actuar_form_changed", "error_message": "Campo de busca do aluno nao foi encontrado."}
        search_input.fill(str(search_value))
        submit = page.locator(ACTUAR_SELECTORS["member_search_submit"]).first
        if submit.count() > 0:
            submit.click()
        else:
            search_input.press("Enter")
        page.wait_for_timeout(500)

        rows = page.locator(ACTUAR_SELECTORS["member_result_row"])
        row_count = rows.count()
        if row_count == 0:
            return {"ok": False, "error_code": "member_not_found", "error_message": "Aluno nao encontrado na aba local do Actuar."}
        if row_count > 1:
            return {"ok": False, "error_code": "member_match_ambiguous", "error_message": "Mais de um aluno foi encontrado no Actuar para o contexto enviado."}

        row = rows.nth(0)
        opener = row.locator(ACTUAR_SELECTORS["member_result_open"]).first
        if opener.count() > 0:
            opener.click()
            page.wait_for_load_state("networkidle")
        return {"ok": True, "external_id": job.get("actuar_external_id") or str(search_value)}

    def _fill_form(self, page, job: dict[str, Any]) -> list[dict[str, Any]]:
        mapped = []
        mapped_fields_json = job.get("mapped_fields_json") or {}
        if isinstance(mapped_fields_json, dict):
            mapped = mapped_fields_json.get("mapped_fields") or []
        action_log: list[dict[str, Any]] = []
        for item in mapped:
            actuar_field = item.get("actuar_field")
            if not actuar_field:
                continue
            selector = ACTUAR_FIELD_SELECTORS.get(actuar_field)
            if not selector:
                continue
            locator = page.locator(selector).first
            if locator.count() == 0:
                if item.get("required"):
                    raise RuntimeError("actuar_form_changed")
                continue
            value = item.get("value")
            if value is None:
                continue
            locator.fill(str(value))
            action_log.append({"event": "filled", "field": item.get("field"), "actuar_field": actuar_field})
        return action_log


def _normalize_document(value: Any) -> str | None:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits or None
