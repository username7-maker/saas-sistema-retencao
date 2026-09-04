import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models import RoleEnum
from app.services.message_template_service import (
    effective_template,
    ensure_domain_permission,
    get_template_definition,
    render_message,
)


def test_template_requires_first_name():
    definition = get_template_definition("retention.reengagement")
    with pytest.raises(ValueError, match="first_name"):
        render_message(definition, definition.content, {})


def test_template_rejects_unknown_placeholder():
    definition = get_template_definition("retention.reengagement")
    with pytest.raises(ValueError, match="não permitidas"):
        render_message(definition, "Oi, {cpf}", {"first_name": "Ana", "cpf": "x"})


def test_receptionist_cannot_use_finance_domain():
    user = SimpleNamespace(role=RoleEnum.RECEPTIONIST)
    with pytest.raises(PermissionError):
        ensure_domain_permission(user, "finance")


def test_effective_template_uses_gym_override():
    db = MagicMock()
    db.scalar.return_value = SimpleNamespace(content="Olá, {first_name}!")
    definition, content, origin = effective_template(db, uuid.uuid4(), "retention.reengagement")
    assert definition.domain == "retention"
    assert content == "Olá, {first_name}!"
    assert origin == "template_gym_override"
