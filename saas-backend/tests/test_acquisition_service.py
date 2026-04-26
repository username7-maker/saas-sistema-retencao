import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models import Lead, LeadBooking, LeadStage
from app.schemas.acquisition import AcquisitionCaptureInput
from app.services.acquisition_service import (
    capture_acquisition_lead,
    generate_acquisition_qualification,
    summarize_acquisition_lead,
)


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


class FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.flushed = 0

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed += 1
        now = datetime.now(tz=timezone.utc)
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
                obj.updated_at = now
            if hasattr(obj, "confirmed_at") and getattr(obj, "confirmed_at", None) is None:
                obj.confirmed_at = now

    def refresh(self, _obj):
        return None

    def commit(self):
        self.committed = True


def test_generate_acquisition_qualification_hot_with_trial_booking():
    payload = AcquisitionCaptureInput(
        full_name="Maria Teste",
        email="maria@example.com",
        phone="11999998888",
        source="landing_page",
        channel="instagram",
        campaign="desafio_verao",
        desired_goal="Emagrecer com acompanhamento",
        preferred_shift="noite",
        trial_interest=True,
        scheduled_for=datetime.now(tz=timezone.utc) + timedelta(days=2),
        consent_communication=True,
        qualification_answers={"urgency": "essa semana"},
    )

    qualification = generate_acquisition_qualification(payload)

    assert qualification.score == 100
    assert qualification.label == "hot"
    assert qualification.recommended_stage == LeadStage.TRIAL.value
    assert "Aula experimental ja agendada." in qualification.reasons


def test_generate_acquisition_qualification_cold_marks_missing_fields():
    payload = AcquisitionCaptureInput(full_name="Lead Frio", source="site")

    qualification = generate_acquisition_qualification(payload)

    assert qualification.score < 45
    assert qualification.label == "cold"
    assert "telefone" in qualification.missing_fields
    assert "aula_experimental" in qualification.missing_fields


def test_capture_acquisition_lead_creates_lead_booking_and_summary():
    db = FakeSession()
    scheduled_for = datetime.now(tz=timezone.utc) + timedelta(days=1)
    payload = AcquisitionCaptureInput(
        full_name="Carlos Trial",
        email="carlos@example.com",
        phone="54999990000",
        source="landing_page",
        channel="google",
        campaign="campanha_trial",
        desired_goal="Ganhar massa",
        preferred_shift="manha",
        trial_interest=True,
        scheduled_for=scheduled_for,
        estimated_value=Decimal("199.90"),
    )

    result = capture_acquisition_lead(db, payload, gym_id=GYM_ID, commit=False)

    lead = next(obj for obj in db.added if isinstance(obj, Lead))
    booking = next(obj for obj in db.added if isinstance(obj, LeadBooking))
    assert lead.gym_id == GYM_ID
    assert lead.stage == LeadStage.TRIAL
    assert booking.gym_id == GYM_ID
    assert booking.lead_id == lead.id
    assert result.summary.channel == "google"
    assert result.summary.has_trial_booking is True
    assert result.summary.next_booking_at == scheduled_for
    assert db.committed is False


def test_summarize_acquisition_lead_reads_latest_notes():
    lead = Lead(
        id=uuid.uuid4(),
        gym_id=GYM_ID,
        full_name="Ana Lead",
        email="ana@example.com",
        phone="11999990000",
        source="instagram",
        stage=LeadStage.NEW,
        notes=[
            {"type": "acquisition_capture", "channel": "facebook", "campaign": "antiga"},
            {
                "type": "acquisition_capture",
                "channel": "instagram",
                "campaign": "nova",
                "preferred_shift": "tarde",
                "consent_communication": True,
            },
            {
                "type": "acquisition_qualification",
                "score": 75,
                "label": "hot",
                "next_action": "Confirmar aula experimental.",
                "reasons": ["Origem rastreavel."],
                "missing_fields": [],
            },
        ],
    )

    summary = summarize_acquisition_lead(lead)

    assert summary.channel == "instagram"
    assert summary.campaign == "nova"
    assert summary.preferred_shift == "tarde"
    assert summary.qualification_score == 75
    assert summary.qualification_label == "hot"
