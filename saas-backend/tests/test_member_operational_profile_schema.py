from datetime import UTC, datetime

from app.schemas.member_operational_profile import MemberOperationalProfileOut


def test_operational_profile_accepts_member_intelligence_flag_codes() -> None:
    payload = {
        "generated_at": datetime.now(tz=UTC),
        "member": {},
        "permissions": {},
        "summary": {},
        "lifecycle": {},
        "risk": {},
        "activity": {},
        "assessment": {},
        "communication": {},
        "tasks": {},
        "autopilot": {},
        "next_best_action": {},
        "data_quality_flags": ["missing_recent_checkin", "missing_assessment"],
    }

    result = MemberOperationalProfileOut.model_validate(payload)

    assert result.data_quality_flags == ["missing_recent_checkin", "missing_assessment"]
