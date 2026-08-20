from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from app.schemas.settings import KommoTrainerRouteUpdate
from app.services.kommo_settings_service import _upsert_trainer_routes, serialize_kommo_settings


def _gym(**overrides):
    payload = {
        "kommo_enabled": True,
        "kommo_base_url": None,
        "kommo_access_token_encrypted": None,
        "kommo_default_pipeline_id": None,
        "kommo_default_stage_id": None,
        "kommo_default_responsible_user_id": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def test_serialize_kommo_settings_reports_ready_when_configured():
    gym = _gym(
        kommo_enabled=True,
        kommo_base_url="crm.kommo.example",
        kommo_access_token_encrypted="secret-token",
        kommo_default_pipeline_id="111",
        kommo_default_stage_id="222",
    )

    payload = serialize_kommo_settings(gym)

    assert payload.kommo_enabled is True
    assert payload.kommo_base_url == "https://crm.kommo.example"
    assert payload.kommo_has_access_token is True
    assert payload.automatic_handoff_ready is True
    assert payload.kommo_default_pipeline_id == "111"
    assert payload.kommo_default_stage_id == "222"


def test_serialize_kommo_settings_reports_not_ready_without_token():
    gym = _gym(kommo_enabled=True, kommo_base_url="https://crm.kommo.example", kommo_access_token_encrypted=None)

    payload = serialize_kommo_settings(gym)

    assert payload.kommo_has_access_token is False
    assert payload.automatic_handoff_ready is False


def test_serialize_kommo_settings_includes_trainer_routes_from_active_trainers():
    trainer_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    trainer = SimpleNamespace(id=trainer_id, full_name="Professora Ana")
    route = SimpleNamespace(
        trainer_user_id=trainer_id,
        is_enabled=True,
        pipeline_id="100",
        stage_id="200",
        salesbot_id="300",
        channel_source_id=None,
        responsible_user_id="400",
        message_field_id="500",
        pdf_url_field_id=None,
        pdf_delivery_mode="native_file_required",
        file_uuid_field_id=None,
        file_name_field_id=None,
        file_attachment_note_field_id=None,
        source_type_field_id=None,
        source_id_field_id=None,
        tags=["tecnico"],
    )
    db = SimpleNamespace(
        scalars=lambda _statement: SimpleNamespace(all=lambda: [trainer] if not hasattr(db, "_seen") else [route])
    )
    db._seen = False

    def _scalars(_statement):
        if not db._seen:
            db._seen = True
            return SimpleNamespace(all=lambda: [trainer])
        return SimpleNamespace(all=lambda: [route])

    db.scalars = _scalars

    payload = serialize_kommo_settings(_gym(id=UUID("11111111-1111-1111-1111-111111111111")), db=db)

    assert payload.trainer_routes[0].trainer_user_id == trainer_id
    assert payload.trainer_routes[0].trainer_name == "Professora Ana"
    assert payload.trainer_routes[0].route_status == "ready"
    assert payload.trainer_routes[0].ready_for_messages is True


def test_upsert_trainer_routes_rejects_non_trainer_user():
    trainer_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    payload = KommoTrainerRouteUpdate(trainer_user_id=trainer_id, pipeline_id="100")

    class _Db:
        def __init__(self):
            self.calls = 0

        def scalars(self, _statement):
            self.calls += 1
            return SimpleNamespace(all=lambda: [])

    db = _Db()

    try:
        _upsert_trainer_routes(db, gym_id=UUID("11111111-1111-1111-1111-111111111111"), payloads=[payload])
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 422
    else:
        raise AssertionError("Expected invalid trainer route to be rejected")
