import uuid
from datetime import datetime, timedelta, timezone

from app.models import Lead, LeadStage, Member, MemberStatus, NPSResponse, NPSSentiment, NPSTrigger, RiskLevel, Task
from app.schemas.growth import GrowthOpportunityPrepareInput
from app.services import growth_service


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
LEAD_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
MEMBER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, *, leads=None, members=None, nps=None):
        self.scalars_responses = [leads or [], members or [], nps or []]
        self.added = []
        self.committed = False
        self.get_map = {}
        self.scalar_response = None
        for lead in leads or []:
            self.get_map[(Lead, lead.id)] = lead
        for member in members or []:
            self.get_map[(Member, member.id)] = member

    def scalars(self, _stmt):
        if not self.scalars_responses:
            return FakeScalarResult([])
        return FakeScalarResult(self.scalars_responses.pop(0))

    def scalar(self, _stmt):
        return self.scalar_response

    def get(self, model, object_id):
        return self.get_map.get((model, object_id))

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()

    def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    def refresh(self, _obj):
        return None

    def commit(self):
        self.committed = True


def _lead(**overrides):
    now = datetime.now(tz=timezone.utc)
    lead = Lead(
        id=LEAD_ID,
        gym_id=GYM_ID,
        full_name="Lead Quente",
        email="lead@example.com",
        phone="54999999999",
        source="instagram",
        stage=LeadStage.TRIAL,
        notes=[
            {
                "type": "acquisition_capture",
                "channel": "instagram",
                "campaign": "desafio",
                "desired_goal": "emagrecer",
                "preferred_shift": "noite",
                "scheduled_for": (now + timedelta(days=1)).isoformat(),
                "consent_communication": True,
            },
            {
                "type": "acquisition_qualification",
                "score": 82,
                "label": "hot",
                "next_action": "Preparar aula experimental.",
            },
        ],
        last_contact_at=now - timedelta(days=1),
    )
    lead.created_at = now - timedelta(days=2)
    lead.updated_at = now - timedelta(days=1)
    for key, value in overrides.items():
        setattr(lead, key, value)
    return lead


def _member(**overrides):
    now = datetime.now(tz=timezone.utc)
    member = Member(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="Aluno Inativo",
        email="aluno@example.com",
        phone="54998887777",
        status=MemberStatus.ACTIVE,
        plan_name="Livre Anual",
        monthly_fee=199,
        join_date=(now - timedelta(days=180)).date(),
        preferred_shift="manha",
        nps_last_score=10,
        loyalty_months=6,
        risk_score=20,
        risk_level=RiskLevel.GREEN,
        last_checkin_at=now - timedelta(days=35),
        extra_data={"consent_communication": True},
    )
    member.created_at = now - timedelta(days=180)
    member.updated_at = now
    for key, value in overrides.items():
        setattr(member, key, value)
    return member


def test_list_growth_audiences_builds_conversion_and_reactivation_items(monkeypatch):
    monkeypatch.setattr(growth_service, "current_consent_status_map", lambda *_args, **_kwargs: {"communication": True})
    db = FakeSession(leads=[_lead()], members=[_member()], nps=[])

    audiences = growth_service.list_growth_audiences(db, gym_id=GYM_ID)

    conversion = next(audience for audience in audiences if audience.id == "conversion_hot_leads")
    reactivation = next(audience for audience in audiences if audience.id == "reactivation_inactive_members")
    assert conversion.count == 1
    assert conversion.items[0].display_name == "Lead Quente"
    assert conversion.items[0].consent_ok is True
    assert reactivation.count == 1
    assert reactivation.items[0].preferred_shift == "manha"


def test_list_growth_audiences_detects_nps_recovery(monkeypatch):
    monkeypatch.setattr(growth_service, "current_consent_status_map", lambda *_args, **_kwargs: {"communication": True})
    member = _member(nps_last_score=9, last_checkin_at=datetime.now(tz=timezone.utc) - timedelta(days=1))
    nps = NPSResponse(
        id=uuid.uuid4(),
        gym_id=GYM_ID,
        member_id=member.id,
        score=4,
        sentiment=NPSSentiment.NEGATIVE,
        trigger=NPSTrigger.MONTHLY,
        response_date=datetime.now(tz=timezone.utc),
    )
    db = FakeSession(leads=[], members=[member], nps=[nps])

    audiences = growth_service.list_growth_audiences(db, gym_id=GYM_ID)

    recovery = next(audience for audience in audiences if audience.id == "nps_recovery")
    assert recovery.count == 1
    assert recovery.items[0].priority == "urgent"
    assert recovery.items[0].channel == "task"


def test_prepare_growth_opportunity_creates_task_and_crm_note():
    lead = _lead()
    db = FakeSession(leads=[lead], members=[], nps=[])

    prepared = growth_service.prepare_growth_opportunity(
        db,
        gym_id=GYM_ID,
        opportunity_id=f"conversion_hot_leads:lead:{LEAD_ID}",
        payload=GrowthOpportunityPrepareInput(create_task=True, operator_note="Chamar ainda hoje."),
        actor_id=uuid.uuid4(),
        actor_name="Comercial",
        actor_role="salesperson",
    )

    task = next(obj for obj in db.added if isinstance(obj, Task))
    assert prepared.task_id == task.id
    assert prepared.crm_note_created is True
    assert prepared.whatsapp_url is not None
    assert any(isinstance(note, dict) and note.get("type") == "growth_prepare" for note in lead.notes)
    assert db.committed is True
