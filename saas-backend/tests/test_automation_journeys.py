from app.models.automation_rule import AutomationAction
from app.schemas.automation import VALID_ACTIONS
from app.services.automation_journey_service import list_journey_templates


def test_send_to_kommo_is_valid_rule_action():
    assert AutomationAction.SEND_TO_KOMMO in VALID_ACTIONS


def test_journey_templates_cover_core_operational_domains():
    templates = {template.id: template for template in list_journey_templates()}

    assert "onboarding_d0_d30" in templates
    assert "retention_absence" in templates
    assert "delinquency" in templates
    assert "commercial" in templates
    assert templates["onboarding_d0_d30"].steps
    assert templates["retention_absence"].domain == "retention"
