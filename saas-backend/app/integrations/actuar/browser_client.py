from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        self.base_url = base_url.rstrip("/")
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
        self._context = self._browser.new_context(ignore_https_errors=True)
        self.page = self._context.new_page()
        self.page.set_default_timeout(self.timeout_ms)

    def login(self, credentials: dict[str, str]) -> None:
        self._ensure_page()
        assert self.page is not None
        self.page.goto(self.base_url, wait_until="networkidle")
        self.page.locator(ACTUAR_SELECTORS["login_username"]).first.fill(credentials["username"])
        self.page.locator(ACTUAR_SELECTORS["login_password"]).first.fill(credentials["password"])
        self.page.locator(ACTUAR_SELECTORS["login_submit"]).first.click()
        self.page.wait_for_load_state("networkidle")

    def find_member(self, link_data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_page()
        assert self.page is not None

        search_value = (
            link_data.get("external_id")
            or normalize_document(link_data.get("document"))
            or link_data.get("full_name")
        )
        if not search_value:
            return {"status": "not_found", "error_code": "member_not_linked"}

        search_input = self.page.locator(ACTUAR_SELECTORS["member_search_input"]).first
        if search_input.count() == 0:
            if link_data.get("external_id"):
                return {"status": "matched", "actuar_external_id": link_data["external_id"], "member_context": {"external_id": link_data["external_id"]}}
            raise RuntimeError("actuar_form_changed")

        search_input.fill(str(search_value))
        submit = self.page.locator(ACTUAR_SELECTORS["member_search_submit"]).first
        if submit.count() > 0:
            submit.click()
        else:
            search_input.press("Enter")
        self.page.wait_for_timeout(500)

        rows = self.page.locator(ACTUAR_SELECTORS["member_result_row"])
        row_count = rows.count()
        if row_count == 0:
            return {"status": "not_found", "error_code": "member_not_found"}
        if row_count > 1:
            return {"status": "ambiguous", "error_code": "member_match_ambiguous"}

        row = rows.nth(0)
        external_id = link_data.get("external_id") or row.get_attribute("data-id") or search_value
        return {
            "status": "matched",
            "actuar_external_id": external_id,
            "member_context": {"external_id": external_id, "search_value": str(search_value)},
            "match_confidence": 1.0 if link_data.get("external_id") else 0.9,
        }

    def open_body_composition_form(self, member_context: dict[str, Any]) -> None:
        self._ensure_page()
        assert self.page is not None
        tab = self.page.locator(ACTUAR_SELECTORS["body_composition_tab"]).first
        if tab.count() == 0:
            raise RuntimeError("actuar_form_changed")
        tab.click()
        self.page.wait_for_load_state("networkidle")
        form = self.page.locator(ACTUAR_SELECTORS["body_composition_form"]).first
        if form.count() == 0:
            raise RuntimeError("actuar_form_changed")

    def fill_body_composition_form(self, mapped_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._ensure_page()
        assert self.page is not None
        action_log: list[dict[str, Any]] = []
        for field in mapped_payload:
            actuar_field = field.get("actuar_field")
            if not actuar_field:
                continue
            selector = ACTUAR_FIELD_SELECTORS.get(actuar_field)
            if not selector:
                continue
            locator = self.page.locator(selector).first
            if locator.count() == 0:
                if field.get("required"):
                    raise RuntimeError("actuar_form_changed")
                continue
            value = field.get("value")
            if value is None:
                if field.get("required"):
                    raise RuntimeError("critical_fields_missing")
                continue
            locator.fill(str(value))
            action_log.append({"field": field.get("field"), "actuar_field": actuar_field, "status": "filled"})
        return action_log

    def save_form(self) -> None:
        self._ensure_page()
        assert self.page is not None
        button = self.page.locator(ACTUAR_SELECTORS["save_button"]).first
        if button.count() == 0:
            raise RuntimeError("actuar_form_changed")
        button.click()
        self.page.wait_for_load_state("networkidle")

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


class ActuarPlaywrightProvider:
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
        self.client.open_body_composition_form(member_context)
        action_log = self.client.fill_body_composition_form(mapped_payload)
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
        return self.client.capture_evidence(evidence_prefix)

    def close(self) -> None:
        self.client.close()
