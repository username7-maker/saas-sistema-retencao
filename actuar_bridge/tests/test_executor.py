from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from actuar_bridge.executor import ACTUAR_FIELD_SELECTORS, ACTUAR_SELECTORS, AttachedActuarBrowserExecutor


class FakeLeafLocator:
    def __init__(self, *, count: int = 1):
        self._count = count
        self.filled: list[str] = []
        self.clicks = 0
        self.presses: list[str] = []

    @property
    def first(self):
        return self

    def count(self) -> int:
        return self._count

    def fill(self, value: str) -> None:
        self.filled.append(value)

    def click(self) -> None:
        self.clicks += 1

    def press(self, key: str) -> None:
        self.presses.append(key)

    def locator(self, _selector: str):
        return FakeLeafLocator(count=0)

    def nth(self, _index: int):
        return self


class FakeRowLocator:
    def __init__(self) -> None:
        self.opener = FakeLeafLocator()

    @property
    def first(self):
        return self

    def count(self) -> int:
        return 1

    def locator(self, _selector: str):
        return self.opener


class FakeCollectionLocator:
    def __init__(self, items: list[object]):
        self.items = items

    @property
    def first(self):
        return self.items[0] if self.items else FakeLeafLocator(count=0)

    def count(self) -> int:
        return len(self.items)

    def nth(self, index: int):
        return self.items[index]


class FakePage:
    def __init__(self, *, url: str):
        self.url = url
        self.default_timeout_ms: int | None = None
        self.search_input = FakeLeafLocator()
        self.search_submit = FakeLeafLocator()
        self.body_tab = FakeLeafLocator()
        self.body_form = FakeLeafLocator()
        self.save_button = FakeLeafLocator()
        self.rows = FakeCollectionLocator([FakeRowLocator()])
        self.field_locators = {
            ACTUAR_FIELD_SELECTORS["weight"]: FakeLeafLocator(),
            ACTUAR_FIELD_SELECTORS["body_fat_percent"]: FakeLeafLocator(),
            ACTUAR_FIELD_SELECTORS["notes"]: FakeLeafLocator(),
        }

    def set_default_timeout(self, timeout_ms: int) -> None:
        self.default_timeout_ms = timeout_ms

    def wait_for_load_state(self, _state: str) -> None:
        return None

    def wait_for_timeout(self, _timeout_ms: int) -> None:
        return None

    def locator(self, selector: str):
        if selector == ACTUAR_SELECTORS["member_search_input"]:
            return self.search_input
        if selector == ACTUAR_SELECTORS["member_search_submit"]:
            return self.search_submit
        if selector == ACTUAR_SELECTORS["member_result_row"]:
            return self.rows
        if selector == ACTUAR_SELECTORS["body_composition_tab"]:
            return self.body_tab
        if selector == ACTUAR_SELECTORS["body_composition_form"]:
            return self.body_form
        if selector == ACTUAR_SELECTORS["save_button"]:
            return self.save_button
        return self.field_locators.get(selector, FakeLeafLocator(count=0))


class FakeBrowser:
    def __init__(self, pages: list[FakePage]):
        self.contexts = [SimpleNamespace(pages=pages)]


class FakeChromium:
    def __init__(self, browser: FakeBrowser):
        self.browser = browser
        self.last_debug_url: str | None = None

    def connect_over_cdp(self, debug_url: str) -> FakeBrowser:
        self.last_debug_url = debug_url
        return self.browser


class FakeSyncPlaywright:
    def __init__(self, browser: FakeBrowser):
        self.chromium = FakeChromium(browser)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _install_fake_playwright(monkeypatch, browser: FakeBrowser) -> None:
    fake_package = ModuleType("playwright")
    fake_sync_api = ModuleType("playwright.sync_api")
    fake_sync_api.sync_playwright = lambda: FakeSyncPlaywright(browser)
    fake_package.sync_api = fake_sync_api
    monkeypatch.setitem(sys.modules, "playwright", fake_package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)


def test_attached_executor_completes_happy_path(monkeypatch):
    page = FakePage(url="https://app.actuar.com/alunos")
    browser = FakeBrowser([page])
    _install_fake_playwright(monkeypatch, browser)

    executor = AttachedActuarBrowserExecutor(debug_url="http://127.0.0.1:9222", timeout_ms=9000)
    result = executor.execute(
        {
            "job_id": "job-1",
            "member_name": "Erick Bedin",
            "actuar_external_id": "act-42",
            "mapped_fields_json": {
                "mapped_fields": [
                    {"field": "weight_kg", "actuar_field": "weight", "value": 84.5},
                    {"field": "body_fat_percent", "actuar_field": "body_fat_percent", "value": 23.0},
                    {"field": "notes", "actuar_field": "notes", "value": "Resumo inicial"},
                ]
            },
        }
    )

    assert result.succeeded is True
    assert result.external_id == "act-42"
    assert page.default_timeout_ms == 9000
    assert page.search_input.filled == ["act-42"]
    assert page.search_submit.clicks == 1
    assert page.body_tab.clicks == 1
    assert page.save_button.clicks == 1
    assert page.field_locators[ACTUAR_FIELD_SELECTORS["weight"]].filled == ["84.5"]
    assert page.field_locators[ACTUAR_FIELD_SELECTORS["body_fat_percent"]].filled == ["23.0"]
    assert page.field_locators[ACTUAR_FIELD_SELECTORS["notes"]].filled == ["Resumo inicial"]
    assert [item["actuar_field"] for item in result.action_log] == ["weight", "body_fat_percent", "notes"]


def test_attached_executor_returns_tab_not_found_when_no_actuar_page(monkeypatch):
    page = FakePage(url="https://example.com/outra-pagina")
    browser = FakeBrowser([page])
    _install_fake_playwright(monkeypatch, browser)

    executor = AttachedActuarBrowserExecutor()
    result = executor.execute({"job_id": "job-2", "member_name": "Aluno Teste"})

    assert result.succeeded is False
    assert result.error_code == "actuar_tab_not_found"
    assert result.manual_fallback is True
