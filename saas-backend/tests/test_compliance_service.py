import uuid
from datetime import datetime, timedelta, timezone

from app.models import Member, MemberConsentRecord, MemberStatus, RiskLevel
from app.schemas.compliance import MemberConsentRecordCreate
from app.services.compliance_service import list_member_consent_records, record_member_consent


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _member():
    return Member(
        id=MEMBER_ID,
        gym_id=GYM_ID,
        full_name="Aluno Compliance",
        email="aluno@example.com",
        plan_name="Plano Base",
        status=MemberStatus.ACTIVE,
        risk_level=RiskLevel.GREEN,
    )


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeSession:
    def __init__(self, records=None):
        self.records = records or []
        self.added = []
        self.committed = False

    def scalar(self, _stmt):
        return _member()

    def scalars(self, _stmt):
        return _ScalarResult(self.records)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        now = datetime.now(tz=timezone.utc)
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = now

    def refresh(self, _obj):
        return None

    def commit(self):
        self.committed = True


def test_list_member_consent_records_marks_missing_and_expired():
    now = datetime.now(tz=timezone.utc)
    records = [
        MemberConsentRecord(
            id=uuid.uuid4(),
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            consent_type="lgpd",
            status="accepted",
            source="manual",
            signed_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=1),
            extra_data={},
            created_at=now - timedelta(days=10),
            updated_at=now - timedelta(days=10),
        ),
        MemberConsentRecord(
            id=uuid.uuid4(),
            gym_id=GYM_ID,
            member_id=MEMBER_ID,
            consent_type="communication",
            status="accepted",
            source="manual",
            signed_at=now,
            extra_data={},
            created_at=now,
            updated_at=now,
        ),
    ]
    summary = list_member_consent_records(FakeSession(records), MEMBER_ID, gym_id=GYM_ID)

    current = {item.consent_type: item for item in summary.current}
    assert current["lgpd"].status == "expired"
    assert current["lgpd"].accepted is False
    assert current["communication"].accepted is True
    assert "image" in summary.missing
    assert "contract" in summary.missing


def test_record_member_consent_is_append_only_and_commit_controlled():
    db = FakeSession()
    payload = MemberConsentRecordCreate(
        consent_type="contract",
        document_title="Contrato Plano Base",
        document_version="2026.04",
        source="frontdesk",
    )

    record = record_member_consent(db, MEMBER_ID, payload, gym_id=GYM_ID, actor_user_id=uuid.uuid4(), commit=False)

    assert record in db.added
    assert record.gym_id == GYM_ID
    assert record.member_id == MEMBER_ID
    assert record.status == "accepted"
    assert record.signed_at is not None
    assert db.committed is False
