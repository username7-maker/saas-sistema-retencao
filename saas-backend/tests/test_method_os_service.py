import uuid
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models import RoleEnum
from app.models.method_os import MethodReport, OperationalEvent, OperationalTask, Person
from app.services import method_os_service


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PERSON_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
EVENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def _owner() -> SimpleNamespace:
    return SimpleNamespace(
        id=USER_ID,
        gym_id=GYM_ID,
        full_name="Owner Teste",
        email="owner@teste.com",
        role=RoleEnum.OWNER,
    )


def _db_with_flush_ids() -> tuple[MagicMock, list[object]]:
    db = MagicMock()
    added: list[object] = []

    def add(obj: object) -> None:
        added.append(obj)

    def flush() -> None:
        now = datetime.now(tz=timezone.utc)
        for obj in added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())
            if isinstance(obj, OperationalTask):
                obj.created_at = now
                obj.updated_at = now
            if isinstance(obj, MethodReport):
                obj.created_at = now

    db.add.side_effect = add
    db.flush.side_effect = flush
    return db, added


def test_method_os_seed_contract_has_six_horizontal_segments() -> None:
    migration_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20260603_0047_cordex_method_os_v1.py"
    spec = spec_from_file_location("cordex_method_os_v1_migration", migration_path)
    assert spec and spec.loader
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    slugs = {item["slug"] for item in migration.SEGMENTS}

    assert slugs == {
        "academia",
        "clinica",
        "estetica",
        "escola_curso",
        "consorcio",
        "servico_b2b_local",
    }
    assert all(item["templates"] for item in migration.SEGMENTS)


def test_event_to_task_generation_stores_pillar_priority_message_and_approval() -> None:
    db, added = _db_with_flush_ids()
    event = OperationalEvent(
        id=EVENT_ID,
        gym_id=GYM_ID,
        person_id=PERSON_ID,
        pillar="sales",
        event_type="proposal_no_response",
        event_source="manual",
        event_payload_json={"proposal_id": "P-123"},
        occurred_at=datetime.now(tz=timezone.utc),
        created_at=datetime.now(tz=timezone.utc),
    )
    person = Person(
        id=PERSON_ID,
        gym_id=GYM_ID,
        name="Maria Silva",
        phone="11 99999-0001",
        person_type="lead",
        status="active",
        metadata_json={},
    )
    db.scalar.side_effect = [event, person]

    output = method_os_service.generate_task_from_event(db, current_user=_owner(), event_id=EVENT_ID, commit=False)
    task = next(obj for obj in added if isinstance(obj, OperationalTask))

    assert output.pillar == "sales"
    assert task.task_type == "follow_up"
    assert task.priority == "high"
    assert task.suggested_message
    assert task.wa_me_link and task.wa_me_link.startswith("https://wa.me/5511999990001?text=")
    assert task.requires_human_approval is True
    assert task.ai_metadata_json["requires_human_approval"] is True
    db.commit.assert_not_called()


def test_weekly_report_uses_method_metrics_and_is_human_reviewed(monkeypatch) -> None:
    db, added = _db_with_flush_ids()
    monkeypatch.setattr(
        method_os_service,
        "_weekly_metrics",
        lambda *_args, **_kwargs: {
            "tasks_created": 8,
            "tasks_completed": 5,
            "leads": 3,
            "opportunities": 2,
            "closed_sales": 1,
            "risk_customers": 4,
            "recovered_customers": 2,
            "bottlenecks": ["2 tarefas vencidas"],
            "recommendations": ["Priorizar contatos sem resposta."],
        },
    )

    report = method_os_service.generate_weekly_report(db, current_user=_owner(), commit=False)

    assert report.requires_human_review is True
    assert "Tarefas criadas: 8" in report.markdown
    assert report.metrics["closed_sales"] == 1
    assert any(isinstance(obj, MethodReport) for obj in added)
    db.commit.assert_not_called()
