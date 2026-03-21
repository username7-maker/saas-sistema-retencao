from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import RoleEnum


TASK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
GYM_ID = UUID("11111111-1111-1111-1111-111111111111")


class TestTaskAssistantRoute:
    def test_requires_authentication(self, client):
        response = client.get(f"/api/v1/tasks/{TASK_ID}/assistant")

        assert response.status_code == 401

    def test_returns_assistant_payload_for_task_context(self, app, client):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        fake_user = SimpleNamespace(
            id=uuid4(),
            gym_id=GYM_ID,
            role=RoleEnum.OWNER,
            is_active=True,
            deleted_at=None,
        )

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: fake_user

        try:
            with (
                patch(
                    "app.routers.tasks.get_task_with_relations_or_404",
                    return_value=SimpleNamespace(id=TASK_ID, gym_id=GYM_ID),
                ),
                patch(
                    "app.routers.tasks.build_task_assistant",
                    return_value={
                        "summary": "Task ligada a onboarding fragil.",
                        "why_it_matters": "A janela de recuperacao ainda e curta.",
                        "next_best_action": "Abrir o perfil e executar a primeira abordagem.",
                        "suggested_message": "Oi Ana, quero te ajudar a voltar ao ritmo.",
                        "evidence": ["Primeira avaliacao pendente", "Check-ins iniciais fracos"],
                        "confidence_label": "Alta",
                        "recommended_channel": "WhatsApp",
                        "cta_target": "/assessments/members/member-1?tab=acoes",
                        "cta_label": "Abrir perfil",
                    },
                ),
            ):
                response = client.get(f"/api/v1/tasks/{TASK_ID}/assistant")

            assert response.status_code == 200
            body = response.json()
            assert body["summary"] == "Task ligada a onboarding fragil."
            assert body["recommended_channel"] == "WhatsApp"
            assert body["cta_target"] == "/assessments/members/member-1?tab=acoes"
        finally:
            app.dependency_overrides.clear()
