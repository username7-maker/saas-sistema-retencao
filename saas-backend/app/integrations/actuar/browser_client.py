from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.config import settings
from app.integrations.actuar.selectors import ACTUAR_FIELD_SELECTORS, ACTUAR_SELECTORS
from app.services.actuar_member_link_service import normalize_document

logger = logging.getLogger(__name__)


class ActuarBrowserClient:
    def __init__(
        self,
        *,
        base_url: str,
        headless: bool = True,
        timeout_seconds: int = 60,
        evidence_dir: str | Path | None = None,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        self.headless = headless
        self.timeout_ms = timeout_seconds * 1000
        self.evidence_dir = Path(evidence_dir or settings.actuar_sync_evidence_dir)
        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None

    def _ensure_page(self) -> None:
        if self.page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("playwright_unavailable") from exc
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        ignore_https_errors = bool(settings.actuar_ignore_https_errors and settings.environment.lower() != "production")
        self._context = self._browser.new_context(ignore_https_errors=ignore_https_errors)
        self.page = self._context.new_page()
        self.page.set_default_timeout(self.timeout_ms)

    def login(self, credentials: dict[str, str]) -> None:
        self._ensure_page()
        assert self.page is not None
        self.page.goto(self.base_url, wait_until="domcontentloaded")
        self.page.wait_for_selector(ACTUAR_SELECTORS["login_username"], state="visible")
        self.page.wait_for_selector(ACTUAR_SELECTORS["login_password"], state="visible")
        self.page.locator(ACTUAR_SELECTORS["login_username"]).first.fill(credentials["username"])
        self.page.locator(ACTUAR_SELECTORS["login_password"]).first.fill(credentials["password"])
        self.page.locator(ACTUAR_SELECTORS["login_submit"]).first.click()
        try:
            self.page.wait_for_function(
                "() => window.location.hash && !window.location.hash.includes('/common/login')",
                timeout=self.timeout_ms,
            )
        except Exception as exc:
            if self._is_on_login_screen():
                raise RuntimeError("actuar_login_failed") from exc
            raise
        if self._is_on_login_screen():
            raise RuntimeError("actuar_login_failed")
        if (self.page.url or "").rstrip("/") != self.base_url:
            self.page.goto(self.base_url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(1000)
            if self._is_on_login_screen():
                raise RuntimeError("actuar_login_failed")
        self._dismiss_global_overlays()

    def find_member(self, link_data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_page()
        assert self.page is not None
        if self._is_on_login_screen():
            raise RuntimeError("actuar_login_failed")

        linked_external_id = _strip_text(link_data.get("external_id"))
        if _looks_like_actuar_person_id(linked_external_id):
            return {
                "status": "matched",
                "actuar_external_id": linked_external_id,
                "member_context": {
                    "external_id": linked_external_id,
                    "person_id": linked_external_id,
                    "profile_url": self._profile_url(linked_external_id),
                },
                "match_confidence": 1.0,
            }

        search_terms = _member_lookup_terms(link_data)
        if not search_terms:
            return {"status": "not_found", "error_code": "member_not_linked"}

        api_candidates = self._fetch_member_candidates_via_api(link_data)
        selected_api_candidate = self._select_member_candidate(api_candidates, link_data)
        if selected_api_candidate:
            person_id = selected_api_candidate["person_id"]
            external_id = linked_external_id or selected_api_candidate.get("external_id") or person_id
            return {
                "status": "matched",
                "actuar_external_id": external_id,
                "member_context": {
                    "external_id": external_id,
                    "person_id": person_id,
                    "profile_url": self._profile_url(person_id),
                },
                "match_confidence": 1.0 if linked_external_id else 0.95,
            }

        self.page.goto(self._assessments_search_url(), wait_until="domcontentloaded")
        self._dismiss_global_overlays()
        search_input = self.page.locator(ACTUAR_SELECTORS["member_search_input"]).first
        if search_input.count() == 0:
            raise RuntimeError("actuar_missing_field:member_search_input")

        last_candidates: list[dict[str, Any]] = []
        for _strategy, search_term in search_terms:
            search_input.fill(search_term)
            search_input.press("Enter")
            self.page.wait_for_timeout(1500)
            self._dismiss_global_overlays()
            candidates = self._collect_member_candidates()
            last_candidates = candidates
            selected = self._select_member_candidate(candidates, link_data)
            if not selected:
                continue
            person_id = selected["person_id"]
            external_id = linked_external_id or selected.get("external_id") or person_id
            return {
                "status": "matched",
                "actuar_external_id": external_id,
                "member_context": {
                    "external_id": external_id,
                    "person_id": person_id,
                    "profile_url": self._profile_url(person_id),
                },
                "match_confidence": 1.0 if linked_external_id else 0.9,
            }

        if len(last_candidates) > 1:
            return {"status": "ambiguous", "error_code": "member_match_ambiguous"}
        return {"status": "not_found", "error_code": "member_not_found"}

    def open_body_composition_form(self, member_context: dict[str, Any]) -> None:
        self._ensure_page()
        assert self.page is not None
        person_id = _strip_text(member_context.get("person_id"))
        self.log_state("before_body_composition_open")

        if person_id and self._navigate_to_route(
            self._body_composition_url(person_id),
            expected_hash=f"/avaliacoes/avaliacao/{person_id}/perimetria",
        ):
            if self._wait_for_body_composition_form_ready(timeout_ms=8000):
                self._ensure_manual_protocol()
                self.log_state("after_body_composition_route")
                return

        self._open_new_assessment(member_context)
        self.log_state("after_new_assessment")
        self._dismiss_profile_overlays()

        if person_id and self._navigate_to_route(
            self._body_composition_url(person_id),
            expected_hash=f"/avaliacoes/avaliacao/{person_id}/perimetria",
        ):
            if self._wait_for_body_composition_form_ready(timeout_ms=max(self.timeout_ms, 10000)):
                self._ensure_manual_protocol()
                self.log_state("after_body_composition_route_post_new_assessment")
                return

        body_composition_clicked = self._click_first_visible(ACTUAR_SELECTORS["body_composition_tab"])
        if not body_composition_clicked:
            body_composition_clicked = self._click_first_matching_text(
                re.compile(r"composi.*corporal.*per[ií]metria", re.IGNORECASE),
                selector="button, a, div, span, [role='button'], [role='tab']",
            )
        if body_composition_clicked:
            self.page.wait_for_load_state("domcontentloaded")
            self.page.wait_for_timeout(1200)
            if self._wait_for_body_composition_form_ready(timeout_ms=max(self.timeout_ms, 10000)):
                self._ensure_manual_protocol()
                self.log_state("after_body_composition_click")
                return

        create_button_clicked = self._click_first_matching_text(re.compile(r"nova\s+avalia|novo\s+exame|adicionar\s+avalia", re.IGNORECASE))
        if create_button_clicked:
            self.page.wait_for_load_state("domcontentloaded")
            self.page.wait_for_timeout(1200)
            if self._wait_for_body_composition_form_ready(timeout_ms=max(self.timeout_ms, 10000)):
                self._ensure_manual_protocol()
                self.log_state("after_body_composition_create")
                return

        if not body_composition_clicked:
            self._log_missing_action("body_composition")
            raise RuntimeError("actuar_missing_action:body_composition")
        self._log_missing_action("body_composition_form")
        raise RuntimeError("actuar_missing_form:body_composition")

    def fill_body_composition_form(self, mapped_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._ensure_page()
        assert self.page is not None
        action_log: list[dict[str, Any]] = []
        direct_fill_count = 0
        needs_body_metrics_refresh = False
        expected_weight = None
        for field in mapped_payload:
            actuar_field = field.get("actuar_field")
            if not actuar_field:
                continue
            if actuar_field in {"notes", "anamnesis_summary"}:
                continue
            if field.get("supported") is False:
                continue
            selector = ACTUAR_FIELD_SELECTORS.get(actuar_field)
            if not selector:
                continue
            locator = self.page.locator(selector).first
            if not self._locator_is_visible(locator):
                continue
            if not self._locator_is_editable(locator):
                action_log.append(
                    {
                        "field": field.get("field"),
                        "actuar_field": actuar_field,
                        "status": "skipped_readonly",
                    }
                )
                continue
            value = field.get("value")
            if value is None:
                continue
            formatted_value = _format_field_value(actuar_field, value)
            if formatted_value is None:
                continue
            try:
                self._fill_input_value(locator, formatted_value)
            except Exception as exc:
                logger.warning(
                    "Actuar field fill failed.",
                    extra={
                        "extra_fields": {
                            "event": "actuar_field_fill_failed",
                            "field": field.get("field"),
                            "actuar_field": actuar_field,
                            "selector": selector,
                            "page_url": self.page.url,
                            "page_hash": self._page_hash(),
                            "error_type": type(exc).__name__,
                            "error_repr": repr(exc)[:500],
                        }
                    },
                )
                raise
            direct_fill_count += 1
            action_log.append({"field": field.get("field"), "actuar_field": actuar_field, "status": "filled"})
            if actuar_field in {"weight", "height_cm"}:
                needs_body_metrics_refresh = True
            if actuar_field == "weight":
                expected_weight = formatted_value
        if direct_fill_count == 0:
            raise RuntimeError("actuar_missing_form:body_composition_fields")
        if needs_body_metrics_refresh and self._refresh_body_metrics(expected_weight=expected_weight):
            action_log.append({"field": "body_metrics", "actuar_field": "update_button", "status": "recalculated"})

        self.log_state("after_fill_body_composition")
        return action_log

    def save_form(self) -> None:
        self._ensure_page()
        assert self.page is not None
        button = self.page.locator(ACTUAR_SELECTORS["save_button"]).first
        if not self._locator_is_visible(button):
            raise RuntimeError("actuar_missing_save_button")
        self.log_state("before_save")
        previous_hash = self._page_hash() or ""
        button.click()
        if not self._wait_for_save_confirmation(previous_hash=previous_hash):
            raise RuntimeError("actuar_save_unconfirmed")
        self.log_state("after_save")

    def capture_evidence(self, prefix: str) -> dict[str, str | None]:
        self._ensure_page()
        assert self.page is not None
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        base_name = f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        screenshot_path = self.evidence_dir / f"{base_name}.png"
        html_path = self.evidence_dir / f"{base_name}.html"
        try:
            self.page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:
            logger.warning("Failed to capture Actuar screenshot.", extra={"extra_fields": {"event": "actuar_evidence_screenshot_failed"}})
            screenshot_path = None  # type: ignore[assignment]
        try:
            html_path.write_text(self.page.content(), encoding="utf-8")
        except Exception:
            logger.warning("Failed to capture Actuar page HTML.", extra={"extra_fields": {"event": "actuar_evidence_html_failed"}})
            html_path = None  # type: ignore[assignment]
        return {
            "screenshot_path": str(screenshot_path) if screenshot_path else None,
            "page_html_path": str(html_path) if html_path else None,
        }

    def _visible_action_texts(self) -> list[str]:
        assert self.page is not None
        try:
            raw_items = self.page.locator("a, button").evaluate_all(
                """
                els => els
                  .map(el => ({
                    text: (el.innerText || '').trim(),
                    visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
                  }))
                  .filter(item => item.visible && item.text)
                  .map(item => item.text)
                """
            )
            unique_items: list[str] = []
            for item in raw_items:
                if item not in unique_items:
                    unique_items.append(item)
            return unique_items[:20]
        except Exception:
            return []

    def _has_any_selector(self, selectors: list[str]) -> bool:
        assert self.page is not None
        for selector in selectors:
            try:
                if self.page.locator(selector).first.count() > 0:
                    return True
            except Exception:
                continue
        return False

    def _wait_for_any_selector(self, selectors: list[str], *, timeout_ms: int) -> bool:
        assert self.page is not None
        deadline = datetime.now(timezone.utc).timestamp() + (timeout_ms / 1000)
        while datetime.now(timezone.utc).timestamp() < deadline:
            if self._has_any_selector(selectors):
                return True
            self.page.wait_for_timeout(250)
        return False

    def _wait_for_any_visible_selector(self, selectors: list[str], *, timeout_ms: int) -> bool:
        assert self.page is not None
        deadline = datetime.now(timezone.utc).timestamp() + (timeout_ms / 1000)
        while datetime.now(timezone.utc).timestamp() < deadline:
            if self._has_any_visible_selector(selectors):
                return True
            self.page.wait_for_timeout(250)
        return False

    def _click_first_visible(self, selector: str) -> bool:
        assert self.page is not None
        try:
            locator = self.page.locator(selector)
            for index in range(locator.count()):
                candidate = locator.nth(index)
                if not self._locator_is_visible(candidate):
                    continue
                if self._click_locator(candidate):
                    return True
            return False
        except Exception:
            return False

    def _click_first_matching_text(self, pattern: re.Pattern[str], *, selector: str = "button, a") -> bool:
        assert self.page is not None
        try:
            locator = self.page.locator(selector).filter(has_text=pattern)
            for index in range(locator.count()):
                candidate = locator.nth(index)
                if not self._locator_is_visible(candidate):
                    continue
                if self._click_locator(candidate):
                    return True
            return False
        except Exception:
            return False

    def _wait_for_body_composition_form_ready(self, *, timeout_ms: int) -> bool:
        return self._wait_for_any_visible_selector(
            [
                ACTUAR_SELECTORS["weight_input"],
                ACTUAR_SELECTORS["protocol_select"],
                ACTUAR_SELECTORS["save_button"],
            ],
            timeout_ms=timeout_ms,
        )

    def _ensure_manual_protocol(self) -> None:
        assert self.page is not None
        select = self.page.locator(ACTUAR_SELECTORS["protocol_select"]).first
        if not self._locator_is_visible(select):
            return
        try:
            select.select_option(value="0: 0")
        except Exception:
            try:
                select.select_option(label="Adicionar manualmente (Balança de Bioimpedância)")
            except Exception:
                return
        self.page.wait_for_timeout(250)
        self._wait_for_any_visible_selector(
            [
                ACTUAR_SELECTORS["weight_input"],
                ACTUAR_SELECTORS["body_fat_percent_input"],
                ACTUAR_SELECTORS["muscle_mass_input"],
            ],
            timeout_ms=5000,
        )

    def _refresh_body_metrics(self, *, expected_weight: str | None) -> bool:
        assert self.page is not None
        button = self.page.locator(ACTUAR_SELECTORS["update_button"]).first
        if not self._locator_is_visible(button):
            return False
        previous_rollup = self._locator_input_value(self.page.locator(ACTUAR_SELECTORS["mass_total_current_input"]).first)
        if not self._click_locator(button):
            return False
        self.page.wait_for_timeout(800)
        self._wait_for_body_metric_rollup(previous_rollup=previous_rollup, expected_weight=expected_weight)
        return True

    def _wait_for_body_metric_rollup(self, *, previous_rollup: str | None, expected_weight: str | None) -> bool:
        assert self.page is not None
        locator = self.page.locator(ACTUAR_SELECTORS["mass_total_current_input"]).first
        if locator.count() == 0:
            return False
        normalized_expected = _normalize_numeric_text(expected_weight)
        normalized_previous = _normalize_numeric_text(previous_rollup)
        deadline = datetime.now(timezone.utc).timestamp() + 8
        while datetime.now(timezone.utc).timestamp() < deadline:
            current_value = self._locator_input_value(locator)
            normalized_current = _normalize_numeric_text(current_value)
            if normalized_expected and normalized_current == normalized_expected:
                return True
            if normalized_current and normalized_current != normalized_previous:
                return True
            self.page.wait_for_timeout(250)
        return False

    def _fill_input_value(self, locator, value: str) -> None:
        locator.click()
        locator.fill(value)
        try:
            locator.dispatch_event("change")
        except Exception:
            pass
        try:
            locator.press("Tab")
        except Exception:
            pass

    def _locator_input_value(self, locator) -> str | None:
        try:
            if locator.count() == 0:
                return None
            return _strip_text(locator.input_value())
        except Exception:
            return None

    def _locator_is_visible(self, locator) -> bool:
        try:
            return locator.count() > 0 and locator.is_visible()
        except Exception:
            return False

    def _click_locator(self, locator) -> bool:
        try:
            locator.scroll_into_view_if_needed()
        except Exception:
            pass
        try:
            locator.click()
            return True
        except TypeError:
            locator.click()
            return True
        except Exception:
            try:
                locator.click(force=True)
                return True
            except TypeError:
                locator.click()
                return True
            except Exception:
                return False

    def _locator_is_editable(self, locator) -> bool:
        try:
            return locator.count() > 0 and locator.is_visible() and locator.is_enabled() and locator.is_editable()
        except Exception:
            return False

    def _has_any_visible_selector(self, selectors: list[str]) -> bool:
        assert self.page is not None
        for selector in selectors:
            try:
                if self._locator_is_visible(self.page.locator(selector).first):
                    return True
            except Exception:
                continue
        return False

    def _open_member_profile(self, member_context: dict[str, Any]) -> None:
        assert self.page is not None
        person_id = _strip_text(member_context.get("person_id"))
        profile_url = _strip_text(member_context.get("profile_url"))
        if not profile_url and person_id:
            profile_url = self._profile_url(person_id)
        if not profile_url:
            raise RuntimeError("member_context_missing")
        self.page.goto(profile_url, wait_until="domcontentloaded")
        self._wait_for_hash_contains("/avaliacoes/perfil-avaliado/", timeout_ms=self.timeout_ms)
        self.page.wait_for_timeout(600)
        self._dismiss_global_overlays()
        if self._is_on_login_screen():
            raise RuntimeError("actuar_login_failed")

    def _open_new_assessment(self, member_context: dict[str, Any]) -> None:
        assert self.page is not None
        if self._open_new_assessment_from_profile(member_context):
            return

        if self._open_new_assessment_from_search(member_context):
            return

        person_id = _strip_text(member_context.get("person_id"))
        if person_id and self._navigate_to_route(self._new_assessment_url(person_id), expected_hash=f"/avaliacoes/avaliacao/{person_id}"):
            if self._wait_for_assessment_page_ready():
                return

        self._log_missing_action("new_assessment")
        raise RuntimeError("actuar_missing_action:new_assessment")

    def _profile_url(self, person_id: str) -> str:
        return f"{self.base_url}/#/avaliacoes/perfil-avaliado/{person_id}"

    def _assessments_search_url(self) -> str:
        return f"{self.base_url}/#/avaliacoes/todas-avaliacoes"

    def _new_assessment_url(self, person_id: str) -> str:
        return f"{self.base_url}/#/avaliacoes/avaliacao/{person_id}"

    def _body_composition_url(self, person_id: str) -> str:
        return f"{self.base_url}/#/avaliacoes/avaliacao/{person_id}/perimetria"

    def _collect_member_candidates(self) -> list[dict[str, Any]]:
        assert self.page is not None
        candidates: list[dict[str, Any]] = []
        cards = self.page.locator(ACTUAR_SELECTORS["member_result_row"])
        for index in range(cards.count()):
            card = cards.nth(index)
            try:
                text = _normalize_text(card.inner_text()) or ""
            except Exception:
                continue
            if not text:
                continue
            link = card.locator(ACTUAR_SELECTORS["member_profile_link"]).first
            href = link.get_attribute("href") if link.count() > 0 else None
            person_id = _extract_person_id_from_href(href)
            if not person_id:
                continue
            candidates.append(
                {
                    "person_id": person_id,
                    "name": _extract_name_from_card(text),
                    "email": _extract_email(text),
                    "age": _extract_age(text),
                    "text": text,
                }
            )
        return _dedupe_member_candidates(candidates)

    def _open_new_assessment_from_search(self, member_context: dict[str, Any]) -> bool:
        assert self.page is not None
        search_term = _resolve_member_search_term(member_context)
        if not search_term:
            return False

        self.page.goto(self._assessments_search_url(), wait_until="domcontentloaded")
        self._wait_for_hash_contains("/avaliacoes/todas-avaliacoes", timeout_ms=self.timeout_ms)
        self._dismiss_global_overlays()
        search_input = self.page.locator(ACTUAR_SELECTORS["member_search_input"]).first
        if not self._locator_is_visible(search_input):
            return False

        search_input.fill("")
        search_input.fill(search_term)
        search_input.press("Enter")
        self.page.wait_for_timeout(1500)
        self._dismiss_global_overlays()

        selected_card = self._find_member_result_card(member_context)
        if selected_card is None:
            return False

        new_assessment = selected_card.locator(ACTUAR_SELECTORS["member_result_new_assessment_button"]).first
        if self._locator_is_visible(new_assessment):
            new_assessment.click()
            self.page.wait_for_load_state("domcontentloaded")
            self._dismiss_global_overlays()
            return self._wait_for_assessment_page_ready()

        # Some Actuar accounts expose a global "Nova Avaliação" CTA after the
        # member row is selected instead of rendering the action inside the card.
        try:
            selected_card.click()
            self.page.wait_for_timeout(600)
        except Exception:
            pass
        if self._click_first_visible(ACTUAR_SELECTORS["new_assessment_button"]):
            self.page.wait_for_load_state("domcontentloaded")
            self._dismiss_global_overlays()
            return self._wait_for_assessment_page_ready()
        if self._click_first_matching_text(re.compile(r"nova\s+avalia", re.IGNORECASE)):
            self.page.wait_for_load_state("domcontentloaded")
            self._dismiss_global_overlays()
            return self._wait_for_assessment_page_ready()

        profile_link = selected_card.locator(ACTUAR_SELECTORS["member_profile_link"]).first
        if not self._locator_is_visible(profile_link):
            return False
        profile_link.click()
        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(1200)
        self._dismiss_global_overlays()

        self._click_first_visible(ACTUAR_SELECTORS["physical_assessment_entry"])
        self.page.wait_for_timeout(800)
        self._dismiss_global_overlays()
        if not self._click_first_visible(ACTUAR_SELECTORS["new_assessment_button"]):
            return False
        self.page.wait_for_load_state("domcontentloaded")
        self._dismiss_global_overlays()
        return self._wait_for_assessment_page_ready()

    def _open_new_assessment_from_profile(self, member_context: dict[str, Any]) -> bool:
        assert self.page is not None
        try:
            self._open_member_profile(member_context)
        except RuntimeError as exc:
            if str(exc) == "actuar_login_failed":
                raise
            return False

        self._dismiss_profile_overlays()
        if not self._wait_for_profile_ready(timeout_ms=min(self.timeout_ms, 15000)):
            return False
        self._dismiss_profile_overlays()

        if not self._click_profile_new_assessment():
            return False

        self.page.wait_for_load_state("domcontentloaded")
        self.page.wait_for_timeout(1200)
        return self._wait_for_assessment_page_ready()

    def _find_member_result_card(self, member_context: dict[str, Any]):
        assert self.page is not None
        cards = self.page.locator(ACTUAR_SELECTORS["member_result_row"])
        expected_person_id = _strip_text(member_context.get("person_id"))
        expected_name = _normalize_text(member_context.get("actuar_search_name") or member_context.get("full_name"))
        expected_email = _normalize_text(member_context.get("email"))

        for index in range(cards.count()):
            card = cards.nth(index)
            card_text = _normalize_text(_safe_inner_text(card)) or ""
            if not card_text:
                continue
            profile_link = card.locator(ACTUAR_SELECTORS["member_profile_link"]).first
            href = profile_link.get_attribute("href") if profile_link.count() > 0 else None
            card_person_id = _extract_person_id_from_href(href)
            if expected_person_id and card_person_id == expected_person_id:
                return card
            if expected_name and expected_name not in card_text:
                continue
            if expected_email:
                card_email = _normalize_text(_extract_email(card_text))
                if card_email and card_email != expected_email:
                    continue
            return card
        return None

    def _wait_for_assessment_page_ready(self) -> bool:
        assert self.page is not None
        deadline = datetime.now(timezone.utc).timestamp() + (self.timeout_ms / 1000)
        while datetime.now(timezone.utc).timestamp() < deadline:
            if self._is_on_login_screen():
                raise RuntimeError("actuar_login_failed")
            self._dismiss_global_overlays()
            visible_actions = [_normalize_text(item) or "" for item in self._visible_action_texts()]
            if self._has_any_visible_selector(
                [
                    ACTUAR_SELECTORS["body_composition_tab"],
                    ACTUAR_SELECTORS["weight_input"],
                    ACTUAR_SELECTORS["protocol_select"],
                    ACTUAR_SELECTORS["save_button"],
                ]
            ):
                return True
            if any("composicao corporal e perimetria" in item for item in visible_actions):
                return True
            body_text = _normalize_text(_safe_body_text(self.page)) or ""
            if _looks_like_new_assessment_menu_surface(body_text):
                return True
            if _looks_like_body_composition_surface(body_text):
                return True
            self.page.wait_for_timeout(500)
        return False

    def _wait_for_profile_ready(self, *, timeout_ms: int) -> bool:
        assert self.page is not None
        deadline = datetime.now(timezone.utc).timestamp() + (timeout_ms / 1000)
        while datetime.now(timezone.utc).timestamp() < deadline:
            if self._is_on_login_screen():
                raise RuntimeError("actuar_login_failed")
            self._dismiss_global_overlays()
            if self._has_blocking_global_overlay():
                self.page.wait_for_timeout(500)
                continue
            if self._has_any_visible_selector([ACTUAR_SELECTORS["new_assessment_button"]]):
                return True
            body_text = _normalize_text(_safe_body_text(self.page)) or ""
            if self._has_any_visible_selector([ACTUAR_SELECTORS["assessment_history_table"]]) and _looks_like_profile_surface(
                body_text,
                self._visible_action_texts(),
            ):
                return True
            self.page.wait_for_timeout(500)
        return False

    def _click_profile_new_assessment(self) -> bool:
        assert self.page is not None
        self._dismiss_global_overlays()
        if self._has_blocking_global_overlay():
            return False
        if self._click_first_visible(ACTUAR_SELECTORS["new_assessment_button"]):
            return True
        if self._click_first_matching_text(re.compile(r"nova\s+avalia", re.IGNORECASE)):
            return True
        if self._click_first_visible(ACTUAR_SELECTORS["physical_assessment_entry"]):
            self.page.wait_for_timeout(800)
            self._dismiss_global_overlays()
            if self._click_first_visible(ACTUAR_SELECTORS["new_assessment_button"]):
                return True
            if self._click_first_matching_text(re.compile(r"nova\s+avalia", re.IGNORECASE)):
                return True
        return False

    def _dismiss_global_overlays(self) -> None:
        assert self.page is not None
        dismiss_patterns = (
            re.compile(r"^ok$", re.IGNORECASE),
            re.compile(r"aceitar", re.IGNORECASE),
            re.compile(r"entendi", re.IGNORECASE),
            re.compile(r"continuar", re.IGNORECASE),
            re.compile(r"fechar", re.IGNORECASE),
            re.compile(r"concordo", re.IGNORECASE),
        )
        dismiss_selectors = "button, a, [role='button'], div[role='button'], span[role='button']"
        for _ in range(4):
            clicked_any = False
            if self._dismiss_cookie_banner():
                clicked_any = True
            for pattern in dismiss_patterns:
                if self._click_first_matching_text(pattern, selector=dismiss_selectors):
                    clicked_any = True
                    self.page.wait_for_timeout(400)
            if not clicked_any:
                break
            if not self._has_blocking_global_overlay():
                break
        if self._has_blocking_global_overlay():
            try:
                self.page.keyboard.press("Escape")
                self.page.wait_for_timeout(250)
            except Exception:
                return

    def _dismiss_profile_overlays(self) -> None:
        self._dismiss_global_overlays()

    def _has_blocking_global_overlay(self) -> bool:
        if self._cookie_banner_visible():
            return True
        actions = [_normalize_text(item) or "" for item in self._visible_action_texts()]
        has_new_assessment = any("nova avalia" in item for item in actions)
        has_privacy_cta = any("privacidade" in item or "politica" in item for item in actions)
        has_ack_cta = any(
            item in {"ok", "entendi"}
            or "aceitar" in item
            or "continuar" in item
            or "fechar" in item
            or "concordo" in item
            for item in actions
        )
        return has_privacy_cta and has_ack_cta and not has_new_assessment

    def _has_blocking_profile_overlay(self) -> bool:
        return self._has_blocking_global_overlay()

    def _cookie_banner_visible(self) -> bool:
        if self.page is None:
            return False
        try:
            banner = self.page.locator("#accept-cookies, .accept-cookies").first
            return self._locator_is_visible(banner)
        except Exception:
            return False

    def _dismiss_cookie_banner(self) -> bool:
        assert self.page is not None
        for selector in (
            "#accept-cookies button",
            "#accept-cookies .btn",
            ".accept-cookies button",
            ".accept-cookies .btn",
        ):
            if self._click_first_visible(selector):
                self.page.wait_for_timeout(400)
                if not self._cookie_banner_visible():
                    return True
        try:
            dismissed = bool(
                self.page.evaluate(
                    """
                    () => {
                      const root = document.querySelector('#accept-cookies, .accept-cookies');
                      if (!root) return false;
                      const button = root.querySelector('button, .btn');
                      if (button) {
                        button.click();
                      }
                      root.remove();
                      return true;
                    }
                    """
                )
            )
        except Exception:
            return False
        if dismissed:
            self.page.wait_for_timeout(400)
        return dismissed

    def _wait_for_save_confirmation(self, *, previous_hash: str) -> bool:
        assert self.page is not None
        deadline = datetime.now(timezone.utc).timestamp() + (self.timeout_ms / 1000)
        while datetime.now(timezone.utc).timestamp() < deadline:
            current_hash = self._page_hash() or ""
            body_text = _normalize_text(_safe_body_text(self.page)) or ""
            if _save_confirmation_visible(previous_hash=previous_hash, current_hash=current_hash, body_text=body_text):
                return True
            self.page.wait_for_timeout(500)
        return False

    def _fetch_member_candidates_via_api(self, link_data: dict[str, Any]) -> list[dict[str, Any]]:
        assert self.page is not None
        headers = _build_actuar_api_headers(_extract_actuar_bearer_token(self.page))
        candidates: list[dict[str, Any]] = []
        external_id = _strip_text(link_data.get("external_id"))
        document = normalize_document(link_data.get("document"))
        full_name = _strip_text(link_data.get("full_name"))
        birthdate = _strip_text(link_data.get("birthdate"))
        external_code = external_id if external_id and re.fullmatch(r"\d+", external_id) else None

        if external_code:
            response = self.page.context.request.get(
                f"{self.base_url.replace('app.actuar.com', 'odata.prd.g.actuar.cloud')}/Pessoas",
                params={
                    "$filter": f"PessoaCd eq {external_code}",
                    "$skip": "0",
                    "$top": "10",
                    "$orderby": "NomeCompleto asc",
                    "$select": "PessoaId,PessoaCd,NomeCompleto,Email,DataNascimento,Cpf",
                },
                headers=headers,
                fail_on_status_code=False,
            )
            if response.ok:
                candidates.extend(
                    _normalize_api_candidates(
                        response.json(),
                        person_id_key="PessoaId",
                        external_id_key="PessoaCd",
                        name_key="NomeCompleto",
                        email_key="Email",
                        age_key="DataNascimento",
                        text_keys=["PessoaCd", "Cpf", "DataNascimento"],
                    )
                )
                deduped = _dedupe_member_candidates(candidates)
                selected = self._select_member_candidate(deduped, link_data)
                if selected:
                    return deduped

        if document:
            response = self.page.context.request.get(
                f"{self.base_url.replace('app.actuar.com', 'odata.prd.g.actuar.cloud')}/Pessoas",
                params={
                    "$filter": f"Cpf eq '{_escape_odata_string(document)}'",
                    "$skip": "0",
                    "$top": "10",
                    "$orderby": "NomeCompleto asc",
                    "$select": "PessoaId,PessoaCd,NomeCompleto,Email,DataNascimento,Cpf",
                },
                headers=headers,
                fail_on_status_code=False,
            )
            if response.ok:
                candidates.extend(
                    _normalize_api_candidates(
                        response.json(),
                        person_id_key="PessoaId",
                        external_id_key="PessoaCd",
                        name_key="NomeCompleto",
                        email_key="Email",
                        age_key="DataNascimento",
                        text_keys=["PessoaCd", "Cpf", "DataNascimento"],
                    )
                )
                deduped = _dedupe_member_candidates(candidates)
                selected = self._select_member_candidate(deduped, link_data)
                if selected:
                    return deduped

        if full_name:
            response = self.page.context.request.get(
                "https://physicalassessmentservice-api.prd.g.actuar.cloud/OData/Persons",
                params={
                    "$filter": f"contains(tolower(FullName), tolower('{_escape_odata_string(full_name)}'))",
                    "$skip": "0",
                    "$top": "25",
                    "$orderby": "FullName asc",
                    "$select": "PersonId,FullName,Birthdate,Email,AssessmentCount",
                },
                headers=headers,
                fail_on_status_code=False,
            )
            if response.ok:
                candidates.extend(
                    _normalize_api_candidates(
                        response.json(),
                        person_id_key="PersonId",
                        external_id_key=None,
                        name_key="FullName",
                        email_key="Email",
                        age_key="Birthdate",
                        text_keys=["Birthdate"],
                    )
                )
        return _dedupe_member_candidates(candidates)

    def _select_member_candidate(self, candidates: list[dict[str, Any]], link_data: dict[str, Any]) -> dict[str, Any] | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        external_id = _strip_text(link_data.get("external_id"))
        normalized_name = _normalize_text(link_data.get("full_name"))
        expected_age = _expected_age(link_data.get("birthdate"))
        document = normalize_document(link_data.get("document"))

        if external_id:
            external_matches = [
                candidate
                for candidate in candidates
                if _strip_text(candidate.get("external_id")) == external_id
            ]
            if len(external_matches) == 1:
                return external_matches[0]

        if document:
            document_matches = [
                candidate
                for candidate in candidates
                if document in (_extract_digits(candidate.get("text")) or "")
            ]
            if len(document_matches) == 1:
                return document_matches[0]

        exact_name_matches = [candidate for candidate in candidates if candidate.get("name") == normalized_name]
        if expected_age is not None:
            age_matches = [candidate for candidate in exact_name_matches if candidate.get("age") == expected_age]
            if len(age_matches) == 1:
                return age_matches[0]
        if len(exact_name_matches) == 1:
            return exact_name_matches[0]
        return None

    def _log_missing_action(self, action_name: str) -> None:
        assert self.page is not None
        logger.warning(
            "Actuar required action not found.",
            extra={
                "extra_fields": {
                    "event": "actuar_action_missing",
                    "action_name": action_name,
                    "page_url": self.page.url,
                    "available_actions": self._visible_action_texts(),
                }
            },
        )

    def log_state(self, label: str) -> None:
        assert self.page is not None
        logger.info(
            "Actuar browser state snapshot.",
            extra={
                "extra_fields": {
                    "event": "actuar_browser_state",
                    "label": label,
                    "page_url": self.page.url,
                    "page_hash": self._page_hash(),
                    "available_actions": self._visible_action_texts(),
                    "visible_fields": self._visible_field_keys(),
                }
            },
        )

    def _navigate_to_route(self, url: str, *, expected_hash: str) -> bool:
        assert self.page is not None
        self.page.goto(url, wait_until="domcontentloaded")
        return self._wait_for_hash_contains(expected_hash, timeout_ms=self.timeout_ms)

    def _wait_for_hash_contains(self, expected_hash: str, *, timeout_ms: int) -> bool:
        assert self.page is not None
        try:
            self.page.wait_for_function(
                "(expected) => (window.location.hash || '').includes(expected)",
                arg=expected_hash,
                timeout=timeout_ms,
            )
            return True
        except Exception:
            return False

    def _page_hash(self) -> str | None:
        assert self.page is not None
        try:
            return _strip_text(self.page.evaluate("() => window.location.hash"))
        except Exception:
            return None

    def _visible_field_keys(self) -> list[str]:
        assert self.page is not None
        visible: list[str] = []
        for field_key, selector in ACTUAR_FIELD_SELECTORS.items():
            try:
                if self.page.locator(selector).first.count() > 0:
                    visible.append(field_key)
            except Exception:
                continue
        return visible

    def _is_on_login_screen(self) -> bool:
        assert self.page is not None
        try:
            current_url = self.page.url or ""
        except Exception:
            current_url = ""
        if "/common/login" in current_url:
            return True
        try:
            password_visible = self.page.locator(ACTUAR_SELECTORS["login_password"]).first.is_visible()
        except Exception:
            password_visible = False
        return password_visible

    def close(self) -> None:
        if self.page is not None:
            try:
                self.page.close()
            except Exception:
                pass
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass


def _normalize_api_candidates(
    payload: Any,
    *,
    person_id_key: str,
    external_id_key: str | None,
    name_key: str,
    email_key: str,
    age_key: str,
    text_keys: list[str],
) -> list[dict[str, Any]]:
    raw_items = payload.get("value") if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        return []

    candidates: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        person_id = _strip_text(item.get(person_id_key))
        if not person_id:
            continue
        parts = [_strip_text(item.get(name_key)), _strip_text(item.get(email_key))]
        parts.extend(_strip_text(item.get(key)) for key in text_keys)
        candidates.append(
            {
                "person_id": person_id,
                "external_id": _strip_text(item.get(external_id_key)) if external_id_key else None,
                "name": _normalize_text(item.get(name_key)) or "",
                "email": _normalize_text(item.get(email_key)),
                "age": _coerce_candidate_age(item.get(age_key)),
                "text": _normalize_text(" ".join(part for part in parts if part)) or "",
            }
        )
    return _dedupe_member_candidates(candidates)


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


def _extract_person_id_from_href(href: str | None) -> str | None:
    if not href:
        return None
    match = re.search(r"/avaliacoes/perfil-avaliado/([^/?#]+)", href)
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


def _dedupe_member_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for candidate in candidates:
        person_id = _strip_text(candidate.get("person_id"))
        if not person_id or person_id in seen:
            continue
        seen.add(person_id)
        ordered.append(candidate)
    return ordered


def _member_lookup_terms(link_data: dict[str, Any]) -> list[tuple[str, str]]:
    candidates = [
        ("document", normalize_document(link_data.get("document"))),
        ("full_name", _strip_text(link_data.get("full_name"))),
    ]
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for strategy, value in candidates:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append((strategy, value))
    return ordered


def _resolve_member_search_term(member_context: dict[str, Any]) -> str | None:
    candidates = [
        _strip_text(member_context.get("actuar_search_name")),
        _strip_text(member_context.get("full_name")),
        normalize_document(member_context.get("document")),
        _strip_text(member_context.get("external_id")),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    return None


def _looks_like_actuar_person_id(value: Any) -> bool:
    raw = _strip_text(value)
    return bool(raw and re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", raw, flags=re.IGNORECASE))


def _format_field_value(actuar_field: str, value: Any) -> str | None:
    if value is None or value == "":
        return None
    if actuar_field == "height_cm":
        try:
            return str(int(round(float(value))))
        except (TypeError, ValueError):
            return None
    if actuar_field in {
        "weight",
        "target_weight_kg",
        "body_fat_percent",
        "fat_mass_kg",
        "muscle_mass_kg",
        "lean_mass_kg",
        "bmi",
        "body_water_percent",
        "bmr_kcal",
        "total_energy_kcal",
    }:
        try:
            return f"{float(value):.2f}".replace(".", ",")
        except (TypeError, ValueError):
            return None
    return _strip_text(value)


def _normalize_numeric_text(value: Any) -> str | None:
    raw = _strip_text(value)
    if not raw:
        return None
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        return f"{float(normalized):.2f}"
    except (TypeError, ValueError):
        return raw


def _looks_like_body_composition_surface(body_text: str | None) -> bool:
    normalized = _normalize_text(body_text) or ""
    if not normalized:
        return False
    if "composição corporal e perimetria" in normalized or "composicao corporal e perimetria" in normalized:
        return True
    if "dobras cutâneas" in normalized and "perimetria" in normalized:
        return True
    return "massa total" in normalized and ("percentual de gordura" in normalized or "massa muscular" in normalized)


def _looks_like_profile_surface(body_text: str | None, visible_actions: list[str] | None = None) -> bool:
    normalized = _normalize_text(body_text) or ""
    if "perfil avaliado" in normalized and "avaliacoes realizadas" in normalized:
        return True
    actions = [_normalize_text(item) or "" for item in (visible_actions or [])]
    return any("nova avalia" in item for item in actions)


def _looks_like_new_assessment_menu_surface(body_text: str | None) -> bool:
    normalized = _normalize_text(body_text) or ""
    if "nova avaliacao" not in normalized:
        return False
    return "composicao corporal e perimetria" in normalized and "anamnese" in normalized


def _save_confirmation_visible(*, previous_hash: str, current_hash: str, body_text: str | None) -> bool:
    normalized = _normalize_text(body_text) or ""
    if "avaliacao salva com sucesso" in normalized:
        return True
    if current_hash and current_hash != previous_hash:
        if "/avaliacoes/avaliacao/" in current_hash and not current_hash.endswith("/perimetria"):
            return True
        if "editar avaliação" in normalized or "editar avaliacao" in normalized:
            return True
    return False


def _build_anamnesis_summary_text(mapped_payload: list[dict[str, Any]]) -> str:
    label_map = {
        "evaluation_date": "Data da avaliacao",
        "weight_kg": "Peso (kg)",
        "height_cm": "Altura (cm)",
        "body_fat_kg": "Gordura corporal (kg)",
        "body_fat_pct": "Percentual de gordura",
        "muscle_mass_kg": "Massa muscular (kg)",
        "lean_mass_kg": "Massa magra (kg)",
        "body_water_pct": "Agua corporal (%)",
        "bmi": "IMC",
        "bmr_kcal": "Taxa metabolica basal (kcal)",
        "total_energy_kcal": "Gasto energetico total (kcal)",
        "visceral_fat": "Gordura visceral",
        "notes": "Observacoes",
    }
    lines = ["Bioimpedancia importada pelo AI GYM OS:"]
    for item in mapped_payload:
        value = item.get("value")
        if value is None or value == "":
            continue
        field_key = item.get("field") or item.get("actuar_field") or "campo"
        label = label_map.get(field_key, field_key.replace("_", " ").capitalize())
        formatted = _format_field_value(item.get("actuar_field") or field_key, value)
        if formatted is None:
            formatted = _strip_text(value)
        if not formatted:
            continue
        lines.append(f"{label}: {formatted}")
    return "\n".join(lines)


def _normalize_base_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return raw
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/")
        normalized = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
        return normalized.rstrip("/")
    return raw.rstrip("/")


def _safe_inner_text(locator) -> str:
    try:
        return locator.inner_text()
    except Exception:
        return ""


def _safe_body_text(page) -> str:
    try:
        return page.locator("body").inner_text()
    except Exception:
        return ""


def _strip_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_text(value: Any) -> str | None:
    normalized = _strip_text(value)
    if not normalized:
        return None
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.casefold()


def _extract_digits(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits or None


def _escape_odata_string(value: Any) -> str:
    return str(value or "").replace("'", "''")


class ActuarPlaywrightProvider:
    provider_name = "actuar_playwright"
    sync_mode = "playwright"

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        worker_id: str,
        evidence_dir: str | Path,
    ) -> None:
        self._credentials = {"username": username, "password": password}
        self.worker_id = worker_id
        self.client = ActuarBrowserClient(
            base_url=base_url,
            headless=settings.actuar_browser_headless,
            timeout_seconds=settings.actuar_sync_timeout_seconds,
            evidence_dir=evidence_dir,
        )

    def login(self) -> None:
        self.client.login(self._credentials)

    def test_connection(self) -> dict[str, Any]:
        self.login()
        return {
            "provider": self.provider_name,
            "supported": True,
            "mode": self.sync_mode,
        }

    def find_member(self, link_data: dict[str, Any]) -> dict[str, Any]:
        return self.client.find_member(link_data)

    def push_body_composition(
        self,
        *,
        member_context: dict[str, Any],
        mapped_payload: list[dict[str, Any]],
        capture_success: bool = False,
        evidence_prefix: str,
    ) -> dict[str, Any]:
        logger.info(
            "Actuar push body composition started.",
            extra={
                "extra_fields": {
                    "event": "actuar_push_body_composition_started",
                    "external_id": member_context.get("external_id"),
                    "person_id": member_context.get("person_id"),
                    "payload_fields": [item.get("actuar_field") for item in mapped_payload],
                }
            },
        )
        self.client.open_body_composition_form(member_context)
        logger.info(
            "Actuar body composition form opened.",
            extra={"extra_fields": {"event": "actuar_sync_form_opened", "page_url": self.client.page.url, "page_hash": self.client._page_hash()}},
        )
        action_log = self.client.fill_body_composition_form(mapped_payload)
        logger.info(
            "Actuar body composition form filled.",
            extra={"extra_fields": {"event": "actuar_sync_form_filled", "filled_count": len(action_log), "page_url": self.client.page.url, "page_hash": self.client._page_hash()}},
        )
        self.client.save_form()
        evidence = {"screenshot_path": None, "page_html_path": None}
        if capture_success:
            evidence = self.client.capture_evidence(evidence_prefix)
        return {
            "actuar_external_id": member_context.get("external_id"),
            "action_log": action_log,
            **evidence,
        }

    def capture_failure_evidence(self, evidence_prefix: str) -> dict[str, str | None]:
        if self.client.page is None:
            return {"screenshot_path": None, "page_html_path": None}
        try:
            return self.client.capture_evidence(evidence_prefix)
        except Exception:
            logger.warning(
                "Failed to capture Actuar failure evidence.",
                extra={"extra_fields": {"event": "actuar_failure_evidence_capture_failed"}},
            )
            return {"screenshot_path": None, "page_html_path": None}

    def close(self) -> None:
        self.client.close()
