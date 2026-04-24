import re
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.integrations.actuar.browser_client import (
    ACTUAR_SELECTORS,
    ActuarBrowserClient,
    _build_anamnesis_summary_text,
    _format_field_value,
    _looks_like_body_composition_surface,
    _looks_like_new_assessment_menu_surface,
    _looks_like_profile_surface,
    _member_lookup_terms,
    _normalize_base_url,
    _normalize_text,
    _resolve_member_search_term,
    _save_confirmation_visible,
)
from app.services.body_composition_actuar_sync_service import _map_unexpected_error


def test_member_lookup_terms_prioritize_document_and_name_only():
    terms = _member_lookup_terms(
        {
            "document": "123.456.789-00",
            "full_name": "Erick Bedin",
            "birthdate": "1990-01-10",
            "external_id": "csv-export:abc",
        }
    )

    assert terms == [("document", "12345678900"), ("full_name", "Erick Bedin")]


def test_format_field_value_uses_actuar_decimal_convention():
    assert _format_field_value("weight", 84.5) == "84,50"
    assert _format_field_value("target_weight_kg", 78.2) == "78,20"
    assert _format_field_value("fat_mass_kg", 19.46) == "19,46"
    assert _format_field_value("bmi", 26.7) == "26,70"
    assert _format_field_value("height_cm", 176.4) == "176"
    assert _format_field_value("notes", "Observacao livre") == "Observacao livre"


def test_select_member_candidate_uses_name_and_age_when_needed():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    selected = client._select_member_candidate(
        [
            {"person_id": "1", "name": "erick bedin", "age": 20, "text": "Erick Bedin 20 anos"},
            {"person_id": "2", "name": "erick bedin", "age": 36, "text": "Erick Bedin 36 anos"},
        ],
        {"full_name": "Erick Bedin", "birthdate": "1990-01-10"},
    )

    assert selected is not None
    assert selected["person_id"] == "2"


def test_map_unexpected_error_handles_missing_action():
    mapped = _map_unexpected_error(RuntimeError("actuar_missing_action:body_composition"))

    assert mapped.code == "actuar_form_changed"
    assert mapped.retryable is False
    assert mapped.manual_fallback is True
    assert "body_composition" in mapped.message


def test_normalize_base_url_strips_dashboard_hash_route():
    assert _normalize_base_url("https://app.actuar.com/#/dashboard/administrativo") == "https://app.actuar.com"
    assert _normalize_base_url("https://app.actuar.com/") == "https://app.actuar.com"


def test_normalize_text_removes_accents_for_actuar_surface_matching():
    assert _normalize_text("Nova avaliação") == "nova avaliacao"
    assert _normalize_text("Composição corporal e perimetria") == "composicao corporal e perimetria"


def test_new_assessment_selector_supports_route_based_cta():
    selector = ACTUAR_SELECTORS["new_assessment_button"]

    assert 'a.btn-success[href*="#/avaliacoes/avaliacao/"]' in selector
    assert 'Nova avaliação' in selector


def test_update_button_selector_is_available_for_body_metric_recalc():
    selector = ACTUAR_SELECTORS["update_button"]

    assert 'Atualizar' in selector


def test_body_composition_selector_supports_proper_accented_text():
    selector = ACTUAR_SELECTORS["body_composition_tab"]

    assert "Composição corporal e perimetria" in selector
    assert 'div:has-text("Composição corporal e perimetria")' in selector


def test_resolve_member_search_term_prefers_explicit_search_name():
    assert (
        _resolve_member_search_term(
            {
                "actuar_search_name": "Erick Bedin",
                "full_name": "Nome Secundario",
                "external_id": "abc-123",
            }
    )
        == "Erick Bedin"
    )


def test_select_member_candidate_prefers_exact_external_id_match():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")

    selected = client._select_member_candidate(
        [
            {"person_id": "1", "external_id": "1234", "name": "evelane mota alves", "age": 35, "text": "Evelane 1234"},
            {"person_id": "2", "external_id": "6955", "name": "evelane mota alves", "age": 35, "text": "Evelane 6955"},
        ],
        {"full_name": "Evelane Mota Alves", "birthdate": "1990-08-27", "external_id": "6955"},
    )

    assert selected is not None
    assert selected["person_id"] == "2"


def test_build_anamnesis_summary_text_compiles_body_composition_snapshot():
    summary = _build_anamnesis_summary_text(
        [
            {"field": "evaluation_date", "actuar_field": None, "value": "2026-04-02"},
            {"field": "weight_kg", "actuar_field": "weight", "value": 84.5},
            {"field": "body_fat_pct", "actuar_field": "body_fat_percent", "value": 23},
            {"field": "notes", "actuar_field": "notes", "value": "Observacao manual"},
        ]
    )

    assert "Bioimpedancia importada pelo AI GYM OS:" in summary
    assert "Peso (kg): 84,50" in summary
    assert "Percentual de gordura: 23,00" in summary
    assert "Observacoes: Observacao manual" in summary


def test_looks_like_body_composition_surface_recognizes_perimetry_screen():
    assert _looks_like_body_composition_surface("Editar composicao corporal e perimetria")
    assert _looks_like_body_composition_surface("Dobras cutaneas Perimetria Massa Total Percentual de Gordura")
    assert not _looks_like_body_composition_surface("Editar anamnese")


def test_looks_like_profile_surface_recognizes_member_profile():
    assert _looks_like_profile_surface("Perfil Avaliado Erick Bedin Avaliacoes realizadas")
    assert _looks_like_profile_surface("Tela neutra", ["Atualizar", "Nova avaliação", "Comparar"])
    assert not _looks_like_profile_surface("Editar anamnese", ["Salvar"])


def test_looks_like_new_assessment_menu_surface_recognizes_tile_screen():
    assert _looks_like_new_assessment_menu_surface(
        "Nova Avaliação Anamnese Composição corporal e perimetria Força e resistência muscular"
    )
    assert not _looks_like_new_assessment_menu_surface("Editar composição corporal e perimetria")


def test_save_confirmation_visible_accepts_navigation_off_perimetria():
    assert _save_confirmation_visible(
        previous_hash="#/avaliacoes/avaliacao/pessoa/perimetria",
        current_hash="#/avaliacoes/avaliacao/pessoa/019d4f34-b0db-7120-8836-d23132222fdd",
        body_text="",
    )


class _FakeClickable:
    def __init__(self, *, visible: bool):
        self.visible = visible
        self.clicked = False

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return self.visible

    def click(self):
        self.clicked = True


class _FakeLocatorGroup:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]

    def filter(self, **_kwargs):
        return self


class _FakeSearchInput:
    def __init__(self):
        self.value = ""

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return True

    def fill(self, value):
        self.value = value

    def press(self, _key):
        return None


class _FakeInputLocator:
    def __init__(self):
        self.value = ""
        self.events = []

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def is_editable(self):
        return True

    def click(self):
        return None

    def fill(self, value):
        self.value = value

    def dispatch_event(self, event_name):
        self.events.append(event_name)

    def press(self, key):
        self.events.append(f"press:{key}")

    def input_value(self):
        return self.value


class _FakeReadonlyInputLocator(_FakeInputLocator):
    def is_editable(self):
        return False


class _FakeUpdateButton:
    def __init__(self, weight_target):
        self.weight_target = weight_target
        self.current_total_locator = None
        self.clicked = False

    @property
    def first(self):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return True

    def click(self):
        self.clicked = True
        if self.current_total_locator is not None and self.weight_target is not None:
            self.current_total_locator.value = self.weight_target


class _FakeFillPage:
    def __init__(self):
        self.weight = _FakeInputLocator()
        self.height = _FakeInputLocator()
        self.body_fat = _FakeInputLocator()
        self.muscle = _FakeInputLocator()
        self.total_energy = _FakeInputLocator()
        self.target_weight = _FakeInputLocator()
        self.mass_total_current = _FakeReadonlyInputLocator()
        self.update = _FakeUpdateButton("84,50")
        self.update.current_total_locator = self.mass_total_current
        self.timeout_calls = []
        self.url = "https://app.actuar.com/#/avaliacoes/avaliacao/demo/perimetria"

    def locator(self, selector):
        mapping = {
            ACTUAR_SELECTORS["weight_input"]: self.weight,
            ACTUAR_SELECTORS["height_input"]: self.height,
            ACTUAR_SELECTORS["body_fat_percent_input"]: self.body_fat,
            ACTUAR_SELECTORS["muscle_mass_input"]: self.muscle,
            ACTUAR_SELECTORS["total_energy_input"]: self.total_energy,
            ACTUAR_SELECTORS["mass_total_target_input"]: self.target_weight,
            ACTUAR_SELECTORS["mass_total_current_input"]: self.mass_total_current,
            ACTUAR_SELECTORS["update_button"]: self.update,
        }
        return mapping.get(selector, _FakeInvisibleAction())

    def wait_for_timeout(self, timeout, *_args, **_kwargs):
        self.timeout_calls.append(timeout)


class _FakeInvisibleAction:
    @property
    def first(self):
        return self

    def count(self):
        return 1

    def is_visible(self):
        return False

    def get_attribute(self, _name):
        return None


class _FakeSelectedCard:
    def __init__(self):
        self.clicked = False
        self._invisible = _FakeInvisibleAction()

    def locator(self, _selector):
        return self._invisible

    def click(self):
        self.clicked = True


class _FakeSearchPage:
    def __init__(self):
        self.search_input = _FakeSearchInput()

    def goto(self, *_args, **_kwargs):
        return None

    def wait_for_timeout(self, *_args, **_kwargs):
        return None

    def wait_for_load_state(self, *_args, **_kwargs):
        return None

    def locator(self, selector):
        if selector == ACTUAR_SELECTORS["member_search_input"]:
            return self.search_input
        return _FakeInvisibleAction()


class _FakeCookieBannerPage:
    def __init__(self, *, banner_visible: bool = True, button_visible: bool = False):
        self.banner_visible = banner_visible
        self.button_visible = button_visible
        self.evaluate_called = False

    def locator(self, selector):
        if selector == "#accept-cookies, .accept-cookies":
            return _FakeClickable(visible=self.banner_visible)
        if selector in {"#accept-cookies button", "#accept-cookies .btn", ".accept-cookies button", ".accept-cookies .btn"}:
            return _FakeClickable(visible=self.button_visible)
        return _FakeInvisibleAction()

    def wait_for_timeout(self, *_args, **_kwargs):
        return None

    def evaluate(self, _script):
        self.evaluate_called = True
        return True


def test_click_first_visible_skips_hidden_candidates():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    hidden = _FakeClickable(visible=False)
    visible = _FakeClickable(visible=True)

    class _FakePage:
        def locator(self, _selector):
            return _FakeLocatorGroup([hidden, visible])

    client.page = _FakePage()

    assert client._click_first_visible("button:has-text('Nova Avaliação')") is True
    assert hidden.clicked is False
    assert visible.clicked is True


def test_click_first_matching_text_skips_hidden_candidates():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    hidden = _FakeClickable(visible=False)
    visible = _FakeClickable(visible=True)

    class _FakePage:
        def locator(self, _selector):
            return _FakeLocatorGroup([hidden, visible])

    client.page = _FakePage()

    assert client._click_first_matching_text(re.compile(r"ok", re.IGNORECASE)) is True
    assert hidden.clicked is False
    assert visible.clicked is True


def test_has_blocking_profile_overlay_requires_privacy_and_ack_without_new_assessment(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")

    monkeypatch.setattr(client, "_visible_action_texts", lambda: ["política de privacidade", "Ok"])
    assert client._has_blocking_profile_overlay() is True

    monkeypatch.setattr(client, "_visible_action_texts", lambda: ["política de privacidade", "Ok", "Nova Avaliação"])
    assert client._has_blocking_profile_overlay() is False


def test_has_blocking_profile_overlay_returns_true_when_cookie_banner_is_visible(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    client.page = _FakeCookieBannerPage(banner_visible=True)

    monkeypatch.setattr(client, "_visible_action_texts", lambda: [])
    assert client._has_blocking_profile_overlay() is True


def test_dismiss_cookie_banner_uses_dom_fallback_when_button_click_is_not_available():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    page = _FakeCookieBannerPage(button_visible=False)
    client.page = page

    assert client._dismiss_cookie_banner() is True
    assert page.evaluate_called is True


def test_dismiss_global_overlays_acknowledges_privacy_modal(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    client.page = MagicMock()
    overlay_state = {"blocking": True}
    clicked_patterns = []

    monkeypatch.setattr(client, "_dismiss_cookie_banner", lambda: False)

    def _click_pattern(pattern, selector="button, a"):
        clicked_patterns.append(pattern.pattern if hasattr(pattern, "pattern") else str(pattern))
        if "ok" in clicked_patterns[-1].lower():
            overlay_state["blocking"] = False
            return True
        return False

    monkeypatch.setattr(client, "_click_first_matching_text", _click_pattern)
    monkeypatch.setattr(client, "_has_blocking_global_overlay", lambda: overlay_state["blocking"])

    client._dismiss_global_overlays()

    assert any("ok" in pattern.lower() for pattern in clicked_patterns)
    client.page.keyboard.press.assert_not_called()


def test_open_new_assessment_from_search_uses_global_cta_when_row_action_missing(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    selected_card = _FakeSelectedCard()
    client.page = _FakeSearchPage()

    monkeypatch.setattr(client, "_wait_for_hash_contains", lambda *args, **kwargs: None)
    monkeypatch.setattr(client, "_find_member_result_card", lambda _context: selected_card)
    monkeypatch.setattr(
        client,
        "_click_first_visible",
        lambda selector: selector == ACTUAR_SELECTORS["new_assessment_button"],
    )
    monkeypatch.setattr(client, "_wait_for_assessment_page_ready", lambda: True)

    opened = client._open_new_assessment_from_search({"full_name": "Erick Bedin"})

    assert opened is True
    assert selected_card.clicked is True


def test_wait_for_assessment_page_ready_accepts_shell_with_body_composition_action(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    client.page = MagicMock()

    monkeypatch.setattr(client, "_is_on_login_screen", lambda: False)
    monkeypatch.setattr(client, "_dismiss_global_overlays", lambda: None)
    monkeypatch.setattr(client, "_has_any_visible_selector", lambda _selectors: False)
    monkeypatch.setattr(client, "_visible_action_texts", lambda: ["Anamnese", "Composição corporal e perimetria"])

    assert client._wait_for_assessment_page_ready() is True


def test_wait_for_assessment_page_ready_accepts_new_assessment_menu_surface(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    client.page = MagicMock()

    monkeypatch.setattr(client, "_is_on_login_screen", lambda: False)
    monkeypatch.setattr(client, "_dismiss_global_overlays", lambda: None)
    monkeypatch.setattr(client, "_has_any_visible_selector", lambda _selectors: False)
    monkeypatch.setattr(client, "_visible_action_texts", lambda: [])
    monkeypatch.setattr(
        "app.integrations.actuar.browser_client._safe_body_text",
        lambda _page: "Nova Avaliação Anamnese Composição corporal e perimetria",
    )

    assert client._wait_for_assessment_page_ready() is True


def test_fetch_member_candidates_via_api_uses_numeric_external_id_before_name_search():
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    response = SimpleNamespace(
        ok=True,
        json=lambda: {
            "value": [
                {
                    "PessoaId": "c10541ca-9392-4d4c-9234-f6384b453ad1",
                    "PessoaCd": 6955,
                    "NomeCompleto": "Evelane Mota Alves",
                    "Email": "evelanemota032@gmail.com",
                    "DataNascimento": "1990-08-27T03:00:00Z",
                    "Cpf": "05527293371",
                }
            ]
        },
    )
    request = MagicMock()
    request.get.return_value = response
    client.page = MagicMock()
    client.page.context = SimpleNamespace(request=request)
    client.page.evaluate.return_value = None

    candidates = client._fetch_member_candidates_via_api({"external_id": "6955"})

    assert len(candidates) == 1
    assert candidates[0]["person_id"] == "c10541ca-9392-4d4c-9234-f6384b453ad1"
    request.get.assert_called_once()
    assert request.get.call_args.kwargs["params"]["$filter"] == "PessoaCd eq 6955"


def test_open_new_assessment_from_search_dismisses_global_overlay_before_using_search(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    selected_card = _FakeSelectedCard()
    client.page = _FakeSearchPage()
    overlay_state = {"dismissed": False}

    monkeypatch.setattr(client, "_wait_for_hash_contains", lambda *args, **kwargs: None)
    monkeypatch.setattr(client, "_dismiss_global_overlays", lambda: overlay_state.__setitem__("dismissed", True))
    monkeypatch.setattr(
        client,
        "_locator_is_visible",
        lambda locator: overlay_state["dismissed"] if locator is client.page.search_input else locator.is_visible(),
    )
    monkeypatch.setattr(client, "_find_member_result_card", lambda _context: selected_card if overlay_state["dismissed"] else None)
    monkeypatch.setattr(
        client,
        "_click_first_visible",
        lambda selector: selector == ACTUAR_SELECTORS["new_assessment_button"],
    )
    monkeypatch.setattr(client, "_wait_for_assessment_page_ready", lambda: True)

    opened = client._open_new_assessment_from_search({"full_name": "Erick Bedin"})

    assert opened is True
    assert overlay_state["dismissed"] is True
    assert selected_card.clicked is True


def test_fill_body_composition_form_refreshes_body_metrics_after_weight_fill(monkeypatch):
    client = ActuarBrowserClient(base_url="https://app.actuar.com")
    client.page = _FakeFillPage()
    monkeypatch.setattr(client, "log_state", lambda *_args, **_kwargs: None)

    action_log = client.fill_body_composition_form(
        [
            {"field": "weight_kg", "actuar_field": "weight", "value": 84.5, "supported": True},
            {"field": "height_cm", "actuar_field": "height_cm", "value": 178, "supported": True},
            {"field": "body_fat_pct", "actuar_field": "body_fat_percent", "value": 23.0, "supported": True},
            {"field": "muscle_mass_kg", "actuar_field": "muscle_mass_kg", "value": 35.6, "supported": True},
            {"field": "target_weight_kg", "actuar_field": "target_weight_kg", "value": 78.2, "supported": True},
            {"field": "total_energy_kcal", "actuar_field": "total_energy_kcal", "value": 3008, "supported": True},
        ]
    )

    assert client.page.weight.value == "84,50"
    assert client.page.height.value == "178"
    assert client.page.target_weight.value == "78,20"
    assert client.page.total_energy.value == "3008,00"
    assert client.page.update.clicked is True
    assert client.page.mass_total_current.value == "84,50"
    assert any(item["status"] == "recalculated" for item in action_log)
