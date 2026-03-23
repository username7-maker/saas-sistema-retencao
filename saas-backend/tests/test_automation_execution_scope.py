from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.automation_execution_log import AutomationExecutionLog
from app.routers.automations import list_automation_executions


GYM_ID = UUID("11111111-1111-1111-1111-111111111111")


def test_automation_execution_log_is_tenant_scoped():
    from app.database import TENANT_SCOPED_MODELS

    assert AutomationExecutionLog in TENANT_SCOPED_MODELS


def test_list_automation_executions_returns_404_for_rule_outside_tenant():
    db = MagicMock()
    db.scalar.return_value = None
    current_user = SimpleNamespace(gym_id=GYM_ID)

    with pytest.raises(HTTPException) as exc_info:
        list_automation_executions(uuid4(), db, current_user, limit=10)

    assert exc_info.value.status_code == 404


def test_list_automation_executions_filters_logs_by_current_gym():
    db = MagicMock()
    rule_id = uuid4()
    db.scalar.return_value = SimpleNamespace(id=rule_id, gym_id=GYM_ID)
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [
        SimpleNamespace(
            id=uuid4(),
            member_id=uuid4(),
            action_type="send_whatsapp",
            status="sent",
            details={"status": "sent"},
            created_at=SimpleNamespace(isoformat=lambda: "2026-03-23T00:00:00+00:00"),
        )
    ]
    db.scalars.return_value = mock_scalars

    result = list_automation_executions(rule_id, db, SimpleNamespace(gym_id=GYM_ID), limit=5)

    stmt = db.scalars.call_args[0][0]
    where_sql = [str(criteria) for criteria in stmt._where_criteria]

    assert len(result) == 1
    assert any("automation_execution_logs.rule_id" in criteria for criteria in where_sql)
    assert any("automation_execution_logs.gym_id" in criteria for criteria in where_sql)
