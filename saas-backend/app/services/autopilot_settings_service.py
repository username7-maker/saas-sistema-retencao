from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import GymAutopilotSettings
from app.schemas.autopilot import AutopilotSettingsOut, AutopilotSettingsUpdate


def get_or_create_autopilot_settings(db: Session, *, gym_id: UUID, flush: bool = True) -> GymAutopilotSettings:
    settings = db.scalar(select(GymAutopilotSettings).where(GymAutopilotSettings.gym_id == gym_id))
    if settings is not None:
        return settings
    settings = GymAutopilotSettings(gym_id=gym_id)
    db.add(settings)
    if flush:
        db.flush()
    return settings


def get_autopilot_settings(db: Session, *, gym_id: UUID) -> AutopilotSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    return AutopilotSettingsOut.model_validate(settings)


def update_autopilot_settings(db: Session, *, gym_id: UUID, payload: AutopilotSettingsUpdate) -> AutopilotSettingsOut:
    settings = get_or_create_autopilot_settings(db, gym_id=gym_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.add(settings)
    db.flush()
    return AutopilotSettingsOut.model_validate(settings)

