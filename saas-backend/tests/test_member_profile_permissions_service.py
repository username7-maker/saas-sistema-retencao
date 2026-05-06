from types import SimpleNamespace

from app.models import RoleEnum
from app.services.member_profile_permissions_service import build_member_profile_permissions, filter_member_note_for_role


def _user(role: RoleEnum):
    return SimpleNamespace(role=role)


def test_trainer_profile_permissions_hide_finance_and_allow_clinical_notes():
    permissions = build_member_profile_permissions(_user(RoleEnum.TRAINER))

    assert permissions["can_view_clinical"] is True
    assert permissions["can_view_financial"] is False
    assert filter_member_note_for_role("coach", "coach", permissions) is True
    assert filter_member_note_for_role("manager", "manager", permissions) is False


def test_reception_profile_permissions_hide_clinical_notes_and_allow_operations():
    permissions = build_member_profile_permissions(_user(RoleEnum.RECEPTIONIST))

    assert permissions["can_view_contact"] is True
    assert permissions["can_view_financial"] is True
    assert permissions["can_view_clinical"] is False
    assert filter_member_note_for_role("health_context", "coach", permissions) is False
    assert filter_member_note_for_role("retention", "team", permissions) is True
