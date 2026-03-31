from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol


ACTUAR_APP_ORIGIN = "https://app.actuar.com"
ACTUAR_ROUTES = {
    "assessments_search": f"{ACTUAR_APP_ORIGIN}/#/avaliacoes/todas-avaliacoes",
    "new_evaluation": f"{ACTUAR_APP_ORIGIN}/#/avaliacoes/avaliacao/{{person_id}}",
    "body_composition": f"{ACTUAR_APP_ORIGIN}/#/avaliacoes/avaliacao/{{person_id}}/perimetria",
}

ACTUAR_SELECTORS = {
    "member_search_input": 'input[name="search"]',
    "member_card": 'div[id^="card-"]',
    "member_profile_link": 'a[href*="#/avaliacoes/perfil-avaliado/"]',
    "protocol_select": 'select[name="protocoloComposicaoCorporalId"]',
    "weight_input": 'input#massa, input[name="massa"]',
    "height_input": 'input#estatura, input[name="estatura"]',
    "body_fat_percent_input": 'input[name="PercentualGorduraAtual"]',
    "muscle_mass_input": 'input[name="MassaMuscularAtual"]',
    "notes_input": 'textarea[name="notes"], textarea',
    "save_button": 'button.btn.btn-success:has-text("Salvar"), button:has-text("Salvar")',
}

ACTUAR_FIELD_SELECTORS = {
    "weight": ACTUAR_SELECTORS["weight_input"],
    "height_cm": ACTUAR_SELECTORS["height_input"],
    "body_fat_percent": ACTUAR_SELECTORS["body_fat_percent_input"],
    "muscle_mass_kg": ACTUAR_SELECTORS["muscle_mass_input"],
    "notes": ACTUAR_SELECTORS["notes_input"],
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


@dataclass(slots=True)
class MemberCardCandidate:
    person_id: str
    name: str
    email: str | None
    age: int | None
    text: str


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
        except ImportError as exc:  # pragma: no cover
            return BridgeExecutionResult(
                succeeded=False,
                error_code="playwright_unavailable",
                error_message=str(exc),
                retryable=False,
                manual_fallback=True,
            )

        with sync_playwright() as playwright:  # pragma: no cover - exercised only where playwright exists
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

            try:
                page.set_default_timeout(self.timeout_ms)
                person_id, action_log = self._resolve_person_id(page, job)
                self._open_body_composition_page(page, person_id)
                self._ensure_manual_protocol(page)
                action_log.extend(self._fill_form(page, job))
                assessment_id = self._save_and_capture_assessment_id(page, person_id)
                action_log.append({"event": "actuar_new_assessment_created", "person_id": person_id, "assessment_id": assessment_id})
                return BridgeExecutionResult(
                    succeeded=True,
                    external_id=person_id,
                    action_log=action_log,
                )
            except BridgeExecutionError as exc:
                return BridgeExecutionResult(
                    succeeded=False,
                    error_code=exc.code,
                    error_message=exc.message,
                    retryable=exc.retryable,
                    manual_fallback=exc.manual_fallback,
                    action_log=exc.action_log,
                )

    def _find_actuar_page(self, browser) -> Any | None:
        for context in browser.contexts:
            for page in context.pages:
                if self.page_url_hint in (page.url or "").lower():
                    return page
        return None

    def _resolve_person_id(self, page, job: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        external_id = _strip_text(job.get("actuar_external_id"))
        if external_id:
            return external_id, [{"event": "actuar_member_resolved", "strategy": "linked_external_id", "person_id": external_id}]

        member_name = _strip_text(job.get("member_name"))
        if not member_name:
            raise BridgeExecutionError("member_context_missing", "Sem contexto suficiente para localizar o aluno no Actuar.")

        page.goto(ACTUAR_ROUTES["assessments_search"], wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        search_input = page.locator(ACTUAR_SELECTORS["member_search_input"]).first
        if search_input.count() == 0:
            raise BridgeExecutionError("actuar_form_changed", "Campo de busca do avaliado nao foi encontrado.")

        search_input.fill(member_name)
        page.wait_for_timeout(1600)
        candidates = _collect_member_candidates(page)
        selected = _select_member_candidate(candidates, job)
        if selected is None:
            raise BridgeExecutionError(
                "member_match_ambiguous" if len(candidates) > 1 else "member_not_found",
                "Nao foi possivel identificar o aluno correto no Actuar pela lista de avaliados.",
                action_log=[{"event": "candidate_count", "count": len(candidates)}],
            )

        return selected.person_id, [
            {
                "event": "actuar_member_resolved",
                "strategy": "search_results",
                "person_id": selected.person_id,
                "email": selected.email,
                "age": selected.age,
            }
        ]

    def _open_body_composition_page(self, page, person_id: str) -> None:
        page.goto(ACTUAR_ROUTES["body_composition"].format(person_id=person_id), wait_until="domcontentloaded")
        if not self._wait_for_any_selector(
            page,
            [
                ACTUAR_SELECTORS["weight_input"],
                ACTUAR_SELECTORS["protocol_select"],
                ACTUAR_SELECTORS["save_button"],
            ],
            timeout_ms=max(self.timeout_ms, 20000),
        ):
            raise BridgeExecutionError("actuar_form_changed", "Formulario real de composicao corporal nao foi encontrado.")

    def _wait_for_any_selector(self, page, selectors: list[str], *, timeout_ms: int) -> bool:
        deadline = time.monotonic() + (timeout_ms / 1000)
        while time.monotonic() < deadline:
            for selector in selectors:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    return True
            page.wait_for_timeout(250)
        return False

    def _ensure_manual_protocol(self, page) -> None:
        select = page.locator(ACTUAR_SELECTORS["protocol_select"]).first
        if select.count() == 0:
            return
        try:
            select.select_option(value="0: 0")
        except Exception:
            try:
                select.select_option(label="Adicionar manualmente (Balança de Bioimpedância)")
            except Exception:
                return
        page.wait_for_timeout(250)

    def _fill_form(self, page, job: dict[str, Any]) -> list[dict[str, Any]]:
        mapped_fields_json = job.get("mapped_fields_json") or {}
        mapped_fields = mapped_fields_json.get("mapped_fields") if isinstance(mapped_fields_json, dict) else None
        action_log: list[dict[str, Any]] = []
        if not mapped_fields:
            return action_log

        for item in mapped_fields:
            actuar_field = item.get("actuar_field")
            selector = ACTUAR_FIELD_SELECTORS.get(actuar_field or "")
            if not selector:
                continue
            locator = page.locator(selector).first
            if locator.count() == 0:
                if item.get("required"):
                    raise BridgeExecutionError(
                        "actuar_form_changed",
                        f"Campo obrigatorio {actuar_field} nao foi encontrado no Actuar.",
                        action_log=action_log,
                    )
                continue

            raw_value = item.get("value")
            formatted_value = _format_field_value(actuar_field or "", raw_value)
            if formatted_value is None:
                if item.get("required"):
                    raise BridgeExecutionError(
                        "critical_fields_missing",
                        f"Campo obrigatorio {actuar_field} nao chegou com valor valido para o Actuar.",
                        action_log=action_log,
                    )
                continue

            locator.fill(formatted_value)
            action = {"event": "filled", "field": item.get("field"), "actuar_field": actuar_field, "value": formatted_value}
            action_log.append(action)
            if item.get("field") == "height_cm" and item.get("classification") == "critical_derived":
                action_log.append({"event": "height_derived_from_weight_and_bmi", "value": formatted_value})

        page.wait_for_timeout(350)
        return action_log

    def _save_and_capture_assessment_id(self, page, person_id: str) -> str | None:
        button = page.locator(ACTUAR_SELECTORS["save_button"]).first
        if button.count() == 0:
            raise BridgeExecutionError("actuar_form_changed", "Botao Salvar nao foi encontrado no Actuar.")

        button.click()
        try:
            page.wait_for_function(
                """expectedPersonId => {
                    const hash = window.location.hash || "";
                    const prefix = `#/avaliacoes/avaliacao/${expectedPersonId}/`;
                    return hash.startsWith(prefix) && !hash.endsWith("/perimetria");
                }""",
                arg=person_id,
                timeout=self.timeout_ms,
            )
        except Exception as exc:  # pragma: no cover
            raise BridgeExecutionError(
                "actuar_save_not_confirmed",
                "O Actuar nao confirmou a criacao da nova avaliacao no tempo esperado.",
            ) from exc

        return _extract_assessment_id_from_url(page.url, person_id)


@dataclass(slots=True)
class BridgeExecutionError(RuntimeError):
    code: str
    message: str
    action_log: list[dict[str, Any]] = field(default_factory=list)
    retryable: bool = False
    manual_fallback: bool = True


def _collect_member_candidates(page) -> list[MemberCardCandidate]:
    candidates: list[MemberCardCandidate] = []
    cards = page.locator(ACTUAR_SELECTORS["member_card"])
    count = cards.count()
    for index in range(count):
        card = cards.nth(index)
        text = _normalize_text(card.inner_text())
        if not text:
            continue
        link = card.locator(ACTUAR_SELECTORS["member_profile_link"]).first
        href = link.get_attribute("href") if link.count() > 0 else None
        person_id = _extract_person_id_from_href(href)
        if not person_id:
            continue
        candidates.append(
            MemberCardCandidate(
                person_id=person_id,
                name=_extract_name_from_card(text),
                email=_extract_email(text),
                age=_extract_age(text),
                text=text,
            )
        )
    return candidates


def _select_member_candidate(candidates: list[MemberCardCandidate], job: dict[str, Any]) -> MemberCardCandidate | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    normalized_email = _normalize_text(job.get("member_email"))
    if normalized_email:
        email_matches = [candidate for candidate in candidates if _normalize_text(candidate.email) == normalized_email]
        if len(email_matches) == 1:
            return email_matches[0]

    normalized_name = _normalize_text(job.get("member_name"))
    expected_age = _expected_age(job.get("member_birthdate"))
    exact_name_matches = [candidate for candidate in candidates if candidate.name == normalized_name]
    if expected_age is not None:
        age_matches = [candidate for candidate in exact_name_matches if candidate.age == expected_age]
        if len(age_matches) == 1:
            return age_matches[0]
    if len(exact_name_matches) == 1:
        return exact_name_matches[0]
    return None


def _extract_person_id_from_href(href: str | None) -> str | None:
    if not href:
        return None
    match = re.search(r"/avaliacoes/perfil-avaliado/([^/?#]+)", href)
    return match.group(1) if match else None


def _extract_assessment_id_from_url(url: str, person_id: str) -> str | None:
    match = re.search(rf"/avaliacoes/avaliacao/{re.escape(person_id)}/([^/?#]+)$", url)
    return match.group(1) if match else None


def _extract_name_from_card(text: str) -> str:
    return (text.split("\n", 1)[0] or "").strip().casefold()


def _extract_email(text: str) -> str | None:
    match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text, re.IGNORECASE)
    return match.group(0).strip().casefold() if match else None


def _extract_age(text: str) -> int | None:
    match = re.search(r"(\d{1,3})\s+anos", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _expected_age(value: Any) -> int | None:
    birthdate = _coerce_date(value)
    if birthdate is None:
        return None
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def _coerce_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    raw = _normalize_text(value)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return None


def _format_field_value(actuar_field: str, value: Any) -> str | None:
    if value is None or value == "":
        return None
    if actuar_field == "height_cm":
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return None
    if actuar_field in {"weight", "body_fat_percent", "muscle_mass_kg"}:
        try:
            return f"{float(value):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return None
    return _strip_text(value)


def _normalize_text(value: Any) -> str | None:
    normalized = _strip_text(value)
    return normalized.casefold() if normalized else None


def _strip_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
