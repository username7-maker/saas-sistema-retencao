"""Tests for body_composition_service."""

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


class TestCreateBodyComposition:
    @patch("app.services.body_composition_service.get_member_or_404")
    def test_creates(self, mock_get_member):
        mock_get_member.return_value = SimpleNamespace(id=MEMBER_ID)
        db = MagicMock()
        from app.schemas.body_composition import BodyCompositionEvaluationCreate
        payload = BodyCompositionEvaluationCreate(
            evaluation_date=date(2026, 3, 1),
            source="manual",
            weight_kg=80.0,
        )
        from app.services.body_composition_service import create_body_composition_evaluation
        result = create_body_composition_evaluation(db, GYM_ID, MEMBER_ID, payload)
        db.add.assert_called_once()
        db.flush.assert_called_once()


class TestListBodyComposition:
    def test_lists(self):
        db = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        db.scalars.return_value = mock_scalars
        from app.services.body_composition_service import list_body_composition_evaluations
        result = list_body_composition_evaluations(db, GYM_ID, MEMBER_ID)
        assert result == []
