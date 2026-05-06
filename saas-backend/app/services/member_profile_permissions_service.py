from app.models import RoleEnum, User


def build_member_profile_permissions(user: User) -> dict:
    role = user.role
    is_management = role in {RoleEnum.OWNER, RoleEnum.MANAGER}
    is_reception = role == RoleEnum.RECEPTIONIST
    is_trainer = role == RoleEnum.TRAINER
    is_sales = role == RoleEnum.SALESPERSON

    return {
        "role": role.value if hasattr(role, "value") else str(role),
        "can_view_contact": is_management or is_reception or is_trainer or is_sales,
        "can_view_financial": is_management or is_reception,
        "can_view_commercial": is_management or is_sales,
        "can_view_clinical": is_management or is_trainer,
        "can_view_internal_notes": is_management or is_reception or is_trainer,
        "can_create_notes": is_management or is_reception or is_trainer or is_sales,
        "can_use_autopilot": is_management or is_reception or is_trainer,
        "can_pause_autopilot": is_management,
    }


def filter_member_note_for_role(note_type: str, visibility: str, permissions: dict) -> bool:
    if visibility == "manager":
        return bool(permissions.get("can_view_financial")) and permissions.get("role") in {"owner", "manager"}
    if visibility == "coach" or note_type in {"coach", "health_context"}:
        return bool(permissions.get("can_view_clinical"))
    if visibility == "sales" or note_type == "sales_handoff":
        return bool(permissions.get("can_view_commercial"))
    if visibility == "internal" or note_type == "internal":
        return bool(permissions.get("can_view_internal_notes"))
    return True
