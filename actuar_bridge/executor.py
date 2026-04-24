from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol


ACTUAR_APP_ORIGIN = "https://app.actuar.com"
ACTUAR_SERVICES = {
    "odata": "https://odata.prd.g.actuar.cloud",
    "physicalassessment_service": "https://physicalassessmentservice-api.prd.g.actuar.cloud",
}
ACTUAR_ROUTES = {
    "assessments_search": f"{ACTUAR_APP_ORIGIN}/#/avaliacoes/todas-avaliacoes",
    "new_evaluation": f"{ACTUAR_APP_ORIGIN}/#/avaliacoes/avaliacao/{{person_id}}",
    "body_composition": f"{ACTUAR_APP_ORIGIN}/#/avaliacoes/avaliacao/{{person_id}}/perimetria",
}

ACTUAR_SELECTORS = {
    "member_search_input": 'input[name="search"]',
    "member_card": 'div[id^="card-"]',
    "member_profile_link": 'a[href*="#/avaliacoes/perfil-avaliado/"]',
    "protocol_select": ", ".join(
        [
            'select[name="protocoloComposicaoCorporalId"]',
            'select[name="ProtocoloComposicaoCorporalId"]',
            'select[name="BodyCompositionProtocolId"]',
            'select[id*="protocoloComposicaoCorporalId" i]',
            'select[id*="BodyCompositionProtocolId" i]',
        ]
    ),
    "weight_input": ", ".join(
        [
            'input#massa',
            'input[name="massa"]',
            'input[name="Massa"]',
            'input[name="MassaTotalAtual"]',
            'input[name="WeightKg"]',
            'input[id*="massa" i]',
            'input[id*="MassaTotalAtual" i]',
            'input[id*="WeightKg" i]',
        ]
    ),
    "height_input": ", ".join(
        [
            'input#estatura',
            'input[name="estatura"]',
            'input[name="Estatura"]',
            'input[name="HeightCm"]',
            'input[id*="estatura" i]',
            'input[id*="HeightCm" i]',
        ]
    ),
    "body_fat_percent_input": ", ".join(
        [
            'input[name="PercentualGorduraAtual"]',
            'input[name="CurrentFatPercentage"]',
            'input[id*="PercentualGorduraAtual" i]',
            'input[id*="CurrentFatPercentage" i]',
        ]
    ),
    "muscle_mass_input": ", ".join(
        [
            'input[name="MassaMuscularAtual"]',
            'input[name="CurrentMuscleMass"]',
            'input[id*="MassaMuscularAtual" i]',
            'input[id*="CurrentMuscleMass" i]',
        ]
    ),
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
    external_id: str | None = None


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
                person_id, persisted_external_id, action_log = self._resolve_person_id(page, job)
                self._open_body_composition_page(page, person_id)
                self._ensure_manual_protocol(page)
                action_log.extend(self._fill_form(page, job))
                assessment_id = self._save_and_capture_assessment_id(page, person_id)
                action_log.append({"event": "actuar_new_assessment_created", "person_id": person_id, "assessment_id": assessment_id})
                return BridgeExecutionResult(
                    succeeded=True,
                    external_id=persisted_external_id,
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

    def _resolve_person_id(self, page, job: dict[str, Any]) -> tuple[str, str | None, list[dict[str, Any]]]:
        linked_external_id = _strip_text(job.get("actuar_external_id"))
        if _looks_like_actuar_person_id(linked_external_id):
            return linked_external_id, linked_external_id, [
                {
                    "event": "actuar_member_resolved",
                    "strategy": "linked_person_id",
                    "person_id": linked_external_id,
                }
            ]

        api_candidates = _fetch_member_candidates_via_api(page, job)
        selected_api_candidate = _select_member_candidate(api_candidates, job)
        if selected_api_candidate is not None:
            return selected_api_candidate.person_id, (linked_external_id or selected_api_candidate.external_id or selected_api_candidate.person_id), [
                {
                    "event": "actuar_member_resolved",
                    "strategy": "api_lookup",
                    "person_id": selected_api_candidate.person_id,
                    "external_id": selected_api_candidate.external_id,
                    "email": selected_api_candidate.email,
                    "age": selected_api_candidate.age,
                }
            ]

        search_terms = _member_lookup_terms(job)
        if not search_terms:
            raise BridgeExecutionError("member_context_missing", "Sem contexto suficiente para localizar o aluno no Actuar.")

        page.goto(ACTUAR_ROUTES["assessments_search"], wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        search_input = page.locator(ACTUAR_SELECTORS["member_search_input"]).first
        if search_input.count() == 0:
            raise BridgeExecutionError("actuar_form_changed", "Campo de busca do avaliado nao foi encontrado.")

        last_candidates: list[MemberCardCandidate] = []
        for strategy, search_term in search_terms:
            search_input.fill(search_term)
            page.wait_for_timeout(1600)
            candidates = _collect_member_candidates(page)
            last_candidates = candidates
            selected = _select_member_candidate(candidates, job)
            if selected is None:
                continue

            return selected.person_id, (linked_external_id or selected.external_id or selected.person_id), [
                {
                    "event": "actuar_member_resolved",
                    "strategy": strategy,
                    "search_term": search_term,
                    "person_id": selected.person_id,
                    "email": selected.email,
                    "age": selected.age,
                }
            ]

        raise BridgeExecutionError(
            "member_match_ambiguous" if len(last_candidates) > 1 else "member_not_found",
            "Nao foi possivel identificar o aluno correto no Actuar pelos dados disponiveis.",
            action_log=[{"event": "candidate_count", "count": len(last_candidates)}],
        )

    def _open_body_composition_page(self, page, person_id: str) -> None:
        page.goto(ACTUAR_ROUTES["body_composition"].format(person_id=person_id), wait_until="domcontentloaded")
        if self._wait_for_any_selector(
            page,
            [
                ACTUAR_SELECTORS["weight_input"],
                ACTUAR_SELECTORS["protocol_select"],
                ACTUAR_SELECTORS["save_button"],
            ],
            timeout_ms=8000,
        ):
            return

        page.goto(ACTUAR_ROUTES["new_evaluation"].format(person_id=person_id), wait_until="domcontentloaded")
        body_composition_tab = page.locator("button, a").filter(has_text=re.compile(r"composi..o corporal e perimetria", re.IGNORECASE)).first
        if body_composition_tab.count() > 0:
            body_composition_tab.click()
            page.wait_for_timeout(1200)
            if self._wait_for_any_selector(
                page,
                [
                    ACTUAR_SELECTORS["weight_input"],
                    ACTUAR_SELECTORS["protocol_select"],
                    ACTUAR_SELECTORS["save_button"],
                ],
                timeout_ms=max(self.timeout_ms, 10000),
            ):
                return

        create_button = page.locator("button, a").filter(has_text=re.compile(r"nova\s+avalia|novo\s+exame|adicionar\s+avalia", re.IGNORECASE)).first
        if create_button.count() > 0:
            create_button.click()
            page.wait_for_timeout(1200)
            if self._wait_for_any_selector(
                page,
                [
                    ACTUAR_SELECTORS["weight_input"],
                    ACTUAR_SELECTORS["protocol_select"],
                    ACTUAR_SELECTORS["save_button"],
                ],
                timeout_ms=max(self.timeout_ms, 10000),
            ):
                return

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
        self._wait_for_any_selector(
            page,
            [
                ACTUAR_SELECTORS["weight_input"],
                ACTUAR_SELECTORS["body_fat_percent_input"],
                ACTUAR_SELECTORS["muscle_mass_input"],
            ],
            timeout_ms=5000,
        )

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
        text = _normalize_comparable_text(card.inner_text())
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
                external_id=None,
            )
        )
    return candidates


def _fetch_member_candidates_via_api(page, job: dict[str, Any]) -> list[MemberCardCandidate]:
    headers = _build_actuar_api_headers(_extract_actuar_bearer_token(page))
    candidates: list[MemberCardCandidate] = []
    external_code = _resolve_lookup_external_code(job)
    if external_code:
        candidates.extend(_fetch_odata_people_by_code(page, external_code, headers))
        deduped = _dedupe_member_candidates(candidates)
        if deduped:
            return deduped

    document = _resolve_lookup_document(job)
    if document:
        candidates.extend(_fetch_odata_people_by_document(page, document, headers))
        deduped = _dedupe_member_candidates(candidates)
        if deduped:
            return deduped

    email = _strip_text(job.get("member_email"))
    if email:
        candidates.extend(_fetch_odata_people_by_email(page, email, headers))
        deduped = _dedupe_member_candidates(candidates)
        if deduped:
            return deduped

    queries = _build_member_name_queries_for_job(job)
    if not queries:
        return _dedupe_member_candidates(candidates)

    for query in queries:
        candidates.extend(_fetch_odata_people_candidates(page, query, headers))
        candidates.extend(_fetch_physical_assessment_candidates(page, query, headers))
        deduped = _dedupe_member_candidates(candidates)
        if _select_member_candidate(deduped, job) is not None:
            return deduped
    return _dedupe_member_candidates(candidates)


def _fetch_odata_people_candidates(page, name_query: str, headers: dict[str, str]) -> list[MemberCardCandidate]:
    params = {
        "$filter": f"contains(tolower(NomeCompleto), tolower('{_escape_odata_string(name_query)}')) and ((Modulo eq 'Afig') or (Origem eq 'Afig'))",
        "$skip": "0",
        "$top": "25",
        "$orderby": "NomeCompleto asc",
        "$select": "PessoaId,PessoaCd,NomeCompleto,Idade,Email,Cpf,DataNascimento",
    }
    response = page.context.request.get(
        f"{ACTUAR_SERVICES['odata']}/Pessoas",
        params=params,
        headers=headers,
        fail_on_status_code=False,
    )
    if not response.ok:
        return []
    payload = response.json()
    return _normalize_api_candidates(
        payload,
        person_id_key="PessoaId",
        external_id_key="PessoaCd",
        name_key="NomeCompleto",
        email_key="Email",
        age_key="DataNascimento",
        text_keys=["PessoaCd", "Cpf", "DataNascimento"],
    )


def _fetch_physical_assessment_candidates(page, name_query: str, headers: dict[str, str]) -> list[MemberCardCandidate]:
    params = {
        "$filter": f"contains(tolower(FullName), tolower('{_escape_odata_string(name_query)}'))",
        "$skip": "0",
        "$top": "25",
        "$orderby": "FullName asc",
        "$select": "PersonId,FullName,Birthdate,Email,AssessmentCount",
    }
    response = page.context.request.get(
        f"{ACTUAR_SERVICES['physicalassessment_service']}/OData/Persons",
        params=params,
        headers=headers,
        fail_on_status_code=False,
    )
    if not response.ok:
        return []
    payload = response.json()
    return _normalize_api_candidates(
        payload,
        person_id_key="PersonId",
        name_key="FullName",
        email_key="Email",
        age_key="Birthdate",
        text_keys=["Birthdate"],
    )


def _normalize_api_candidates(
    payload: Any,
    *,
    person_id_key: str,
    name_key: str,
    email_key: str,
    age_key: str,
) -> list[MemberCardCandidate]:
    raw_items = payload.get("value") if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        return []

    candidates: list[MemberCardCandidate] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        person_id = _strip_text(item.get(person_id_key))
        if not person_id:
            continue
        raw_name = _strip_text(item.get(name_key))
        raw_email = _strip_text(item.get(email_key))
        raw_age = item.get(age_key)
        candidates.append(
            MemberCardCandidate(
                person_id=person_id,
                name=_normalize_text(raw_name) or "",
                email=_normalize_text(raw_email),
                age=_coerce_candidate_age(raw_age),
                text=_normalize_text(" ".join(part for part in [raw_name, raw_email, str(raw_age or "")] if part)) or "",
            )
        )
    return _dedupe_member_candidates(candidates)


def _select_member_candidate(candidates: list[MemberCardCandidate], job: dict[str, Any]) -> MemberCardCandidate | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    normalized_external_id = _normalize_text(job.get("actuar_external_id"))
    if normalized_external_id and not _looks_like_actuar_person_id(normalized_external_id):
        external_id_matches = [candidate for candidate in candidates if normalized_external_id in candidate.text]
        if len(external_id_matches) == 1:
            return external_id_matches[0]

    normalized_document = _resolve_lookup_document(job)
    if normalized_document:
        document_matches = [
            candidate
            for candidate in candidates
            if (candidate_digits := _extract_digits(candidate.text)) and normalized_document in candidate_digits
        ]
        if len(document_matches) == 1:
            return document_matches[0]

    normalized_email = _normalize_text(job.get("member_email"))
    if normalized_email:
        email_matches = [candidate for candidate in candidates if _normalize_text(candidate.email) == normalized_email]
        if len(email_matches) == 1:
            return email_matches[0]

    normalized_name = _normalize_text(_resolve_lookup_name(job))
    expected_age = _expected_age(_resolve_lookup_birthdate(job))
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


def _dedupe_member_candidates(candidates: list[MemberCardCandidate]) -> list[MemberCardCandidate]:
    seen: set[str] = set()
    ordered: list[MemberCardCandidate] = []
    for candidate in candidates:
        person_id = _strip_text(candidate.person_id)
        if not person_id or person_id in seen:
            continue
        seen.add(person_id)
        ordered.append(candidate)
    return ordered


def _looks_like_actuar_person_id(value: Any) -> bool:
    raw = _strip_text(value)
    return bool(raw and re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", raw, flags=re.IGNORECASE))


def _strip_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _extract_digits(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits or None


def _member_lookup_terms(job: dict[str, Any]) -> list[tuple[str, str]]:
    candidates = [
        ("linked_external_id", _strip_text(job.get("actuar_external_id"))),
        ("actuar_search_document", _resolve_lookup_document(job)),
        ("member_document", _extract_digits(job.get("member_document"))),
        ("member_email", _strip_text(job.get("member_email"))),
        ("actuar_search_name", _strip_text(job.get("actuar_search_name"))),
        ("member_name", _strip_text(job.get("member_name"))),
    ]
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for strategy, value in candidates:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append((strategy, value))
    return ordered


def _build_member_name_queries(value: Any) -> list[str]:
    raw_name = _strip_text(value)
    if not raw_name:
        return []
    tokens = [token for token in raw_name.split() if token]
    return _unique_non_empty(
        [
            raw_name,
            f"{tokens[0]} {tokens[-1]}" if len(tokens) >= 2 else None,
            f"{tokens[0]} {tokens[1]}" if len(tokens) >= 2 else None,
            tokens[0] if tokens else None,
        ]
    )


def _resolve_lookup_name(job: dict[str, Any]) -> str | None:
    return _strip_text(job.get("actuar_search_name")) or _strip_text(job.get("member_name"))


def _resolve_lookup_document(job: dict[str, Any]) -> str | None:
    return _extract_digits(job.get("actuar_search_document")) or _extract_digits(job.get("member_document"))


def _resolve_lookup_birthdate(job: dict[str, Any]) -> Any:
    return _strip_text(job.get("actuar_search_birthdate")) or _strip_text(job.get("member_birthdate"))


def _build_actuar_api_headers(bearer_token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    return headers


def _extract_actuar_bearer_token(page) -> str | None:
    return _strip_text(
        page.evaluate(
            """
            () => {
              const storages = [window.localStorage, window.sessionStorage];
              const candidates = [];

              const decodePayload = (token) => {
                const payloadSegment = String(token || "").split(".")[1];
                if (!payloadSegment) return null;
                try {
                  const base64 = payloadSegment.replace(/-/g, "+").replace(/_/g, "/");
                  const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
                  return JSON.parse(atob(padded));
                } catch (_error) {
                  return null;
                }
              };

              const collectTokens = (value, depth = 0) => {
                if (depth > 4 || value == null) return;
                if (typeof value === "string") {
                  const matches = value.match(/[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+/g) || [];
                  const validMatches = matches.filter((token) => decodePayload(token));
                  if (validMatches.length) {
                    candidates.push(...validMatches);
                    return;
                  }
                  const normalized = String(value).trim();
                  if (!normalized || normalized.length > 12000 || (!normalized.startsWith("{") && !normalized.startsWith("["))) {
                    return;
                  }
                  try {
                    collectTokens(JSON.parse(normalized), depth + 1);
                  } catch (_error) {
                    return;
                  }
                  return;
                }
                if (Array.isArray(value)) {
                  value.forEach((item) => collectTokens(item, depth + 1));
                  return;
                }
                if (typeof value === "object") {
                  Object.values(value).forEach((item) => collectTokens(item, depth + 1));
                }
              };

              for (const storage of storages) {
                if (!storage) continue;
                try {
                  for (let index = 0; index < storage.length; index += 1) {
                    const key = storage.key(index);
                    if (!key) continue;
                    collectTokens(storage.getItem(key));
                  }
                } catch (_error) {}
              }

              const nowSeconds = Math.floor(Date.now() / 1000);
              const unique = [...new Set(candidates.filter(Boolean))];
              const unexpired = unique.filter((token) => {
                const payload = decodePayload(token);
                return !payload?.exp || payload.exp > nowSeconds + 30;
              });
              return unexpired[0] || unique[0] || null;
            }
            """
        )
    )


def _coerce_candidate_age(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    birthdate = _coerce_date(value)
    if birthdate is not None:
        return _expected_age(birthdate)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _escape_odata_string(value: Any) -> str:
    return str(value or "").replace("'", "''")


def _unique_non_empty(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
