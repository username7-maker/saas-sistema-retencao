"""Tests for objection_service helper functions."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.objection_service import (
    _extract_context,
    _keyword_match,
    _normalize_text,
    _render_template,
    generate_objection_response,
    list_admin_objections,
    mark_sequence_completed_if_won,
    update_admin_objection,
)


class TestNormalizeText:
    def test_strips_accents(self):
        assert _normalize_text("café") == "cafe"

    def test_lowercases(self):
        assert _normalize_text("HELLO World") == "hello world"

    def test_collapses_whitespace(self):
        assert _normalize_text("  foo   bar  ") == "foo bar"


class TestKeywordMatch:
    def test_matches_keyword(self):
        obj = SimpleNamespace(trigger_keywords=["caro", "preco"], id=1)
        result = _keyword_match("Acho muito caro o plano", [obj])
        assert result == obj

    def test_no_match(self):
        obj = SimpleNamespace(trigger_keywords=["caro"], id=1)
        result = _keyword_match("Gostei muito", [obj])
        assert result is None

    def test_best_match_longest(self):
        obj1 = SimpleNamespace(trigger_keywords=["caro"], id=1)
        obj2 = SimpleNamespace(trigger_keywords=["muito caro"], id=2)
        result = _keyword_match("Acho muito caro", [obj1, obj2])
        assert result == obj2  # longer keyword wins

    def test_empty_keywords(self):
        obj = SimpleNamespace(trigger_keywords=["", "  "], id=1)
        result = _keyword_match("anything", [obj])
        assert result is None


class TestExtractContext:
    def test_no_lead_id(self):
        db = MagicMock()
        result = _extract_context(db, None, {"key": "value"})
        assert result == {"key": "value"}

    def test_with_lead(self):
        lead = SimpleNamespace(full_name="Joao", stage=SimpleNamespace(value="new"))
        db = MagicMock()
        db.scalar.return_value = None  # no sequence
        db.get.return_value = lead
        result = _extract_context(db, uuid.uuid4(), {})
        assert result["lead_name"] == "Joao"
        assert result["lead_stage"] == "new"

    def test_with_sequence_data(self):
        seq = SimpleNamespace(diagnosis_data={"revenue": 50000})
        lead = SimpleNamespace(full_name="Ana", stage=SimpleNamespace(value="contact"))
        db = MagicMock()
        db.scalar.return_value = seq
        db.get.return_value = lead
        result = _extract_context(db, uuid.uuid4(), {})
        assert result["revenue"] == 50000
        assert result["lead_name"] == "Ana"


class TestRenderTemplate:
    def test_replaces_vars(self):
        result = _render_template("Ola {name}, seu plano e {plan}", {"name": "Joao", "plan": "Premium"})
        assert result == "Ola Joao, seu plano e Premium"

    def test_missing_var_returns_template(self):
        result = _render_template("Ola {name}", {})
        # Falls back to template on error
        assert "Ola" in result


class TestGenerateObjectionResponse:
    @patch("app.services.objection_service.settings")
    def test_keyword_match_rule(self, mock_settings):
        mock_settings.claude_api_key = None
        obj = SimpleNamespace(
            id=uuid.uuid4(), trigger_keywords=["caro"],
            response_template="Entendo que o preco e importante.", is_active=True,
        )
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [obj]
        db.scalars.return_value = mock_scalars
        db.scalar.return_value = None
        db.get.return_value = None

        result = generate_objection_response(db, message_text="Acho caro")
        assert result["matched"] is True
        assert result["source"] == "keyword_rule"

    @patch("app.services.objection_service.settings")
    def test_no_match_returns_generic(self, mock_settings):
        mock_settings.claude_api_key = None
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        result = generate_objection_response(db, message_text="Boa tarde")
        assert result["matched"] is False
        assert result["source"] == "generic"


class TestListAdminObjections:
    def test_lists(self):
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        result = list_admin_objections(db, uuid.uuid4())
        assert result == []


class TestUpdateAdminObjection:
    def test_not_found_raises(self):
        db = MagicMock()
        db.get.return_value = None
        from app.schemas.objection import ObjectionResponseUpdate
        with pytest.raises(HTTPException) as exc_info:
            update_admin_objection(db, objection_id=uuid.uuid4(), admin_gym_id=uuid.uuid4(), payload=ObjectionResponseUpdate())
        assert exc_info.value.status_code == 404

    def test_forbidden_raises(self):
        other_gym = uuid.uuid4()
        obj = SimpleNamespace(id=uuid.uuid4(), gym_id=other_gym)
        db = MagicMock()
        db.get.return_value = obj
        from app.schemas.objection import ObjectionResponseUpdate
        with pytest.raises(HTTPException) as exc_info:
            update_admin_objection(db, objection_id=obj.id, admin_gym_id=uuid.uuid4(), payload=ObjectionResponseUpdate())
        assert exc_info.value.status_code == 403

    def test_updates(self):
        admin_gym = uuid.uuid4()
        obj = SimpleNamespace(id=uuid.uuid4(), gym_id=admin_gym, response_template="old")
        db = MagicMock()
        db.get.return_value = obj
        db.refresh = MagicMock()
        from app.schemas.objection import ObjectionResponseUpdate
        result = update_admin_objection(
            db, objection_id=obj.id, admin_gym_id=admin_gym,
            payload=ObjectionResponseUpdate(response_template="new"),
        )
        assert result.response_template == "new"
        db.commit.assert_called_once()


class TestMarkSequenceCompletedIfWon:
    def test_marks_sequences(self):
        from app.models import LeadStage
        lead = SimpleNamespace(stage=LeadStage.WON)
        seq = SimpleNamespace(completed=False, diagnosis_data={})
        db = MagicMock()
        db.get.return_value = lead
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [seq]
        db.scalars.return_value = mock_scalars
        mark_sequence_completed_if_won(db, uuid.uuid4())
        assert seq.completed is True
        assert seq.diagnosis_data["stop_reason"] == "lead_won"

    def test_no_lead_does_nothing(self):
        db = MagicMock()
        db.get.return_value = None
        mark_sequence_completed_if_won(db, uuid.uuid4())
        db.commit.assert_not_called()
