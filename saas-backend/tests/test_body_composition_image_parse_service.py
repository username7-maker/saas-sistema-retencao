import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.core.dependencies import get_current_user
from app.database import get_db
from app.schemas.body_composition import (
    BodyCompositionImageOcrPayload,
    BodyCompositionImageParseResultRead,
    BodyCompositionOcrValues,
    BodyCompositionOcrWarning,
    BodyCompositionRangeValue,
)


MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _local_ocr_payload(weight_kg: float = 14.41) -> BodyCompositionImageOcrPayload:
    return BodyCompositionImageOcrPayload(
        device_profile="tezewa_receipt_v1",
        device_model="Tezewa",
        values=BodyCompositionOcrValues(
            weight_kg=weight_kg,
            body_fat_kg=19.46,
            body_fat_percent=23.0,
            waist_hip_ratio=0.88,
            health_score=62,
        ),
        ranges={
            "weight_kg": BodyCompositionRangeValue(min=61.7, max=75.5),
            "body_fat_kg": BodyCompositionRangeValue(min=7.55, max=14.41),
        },
        warnings=[
            BodyCompositionOcrWarning(
                field="weight_kg",
                message="OCR local veio ambiguo para peso.",
                severity="critical",
            )
        ],
        confidence=0.48,
        raw_text="Weight (kg) 14.41 7.55-14.41",
        needs_review=True,
    )


def _ai_parse_result(weight_kg: float = 84.5) -> BodyCompositionImageParseResultRead:
    return BodyCompositionImageParseResultRead(
        device_profile="tezewa_receipt_v1",
        device_model="Tezewa",
        values=BodyCompositionOcrValues(
            weight_kg=weight_kg,
            body_fat_kg=19.46,
            body_fat_percent=23.0,
            waist_hip_ratio=0.88,
            target_weight_kg=68.3,
            weight_control_kg=-16.1,
            muscle_control_kg=-7.8,
            fat_control_kg=-8.3,
            total_energy_kcal=3008.0,
            physical_age=26,
            health_score=62,
        ),
        ranges={
            "weight_kg": BodyCompositionRangeValue(min=61.7, max=75.5),
            "body_fat_kg": BodyCompositionRangeValue(min=7.55, max=14.41),
            "body_fat_percent": BodyCompositionRangeValue(min=11.0, max=21.0),
        },
        warnings=[],
        confidence=0.94,
        raw_text="Body composition Weight 84.5",
        needs_review=False,
        engine="ai_assisted",
        fallback_used=False,
    )


def _ai_parse_result_with_extra_values() -> BodyCompositionImageParseResultRead:
    payload = _ai_parse_result()
    payload.values.inorganic_salt_kg = 3.2
    payload.values.muscle_mass_kg = 37.2
    payload.values.protein_kg = 17.7
    payload.values.body_water_kg = 43.3
    payload.values.visceral_fat_level = 9.1
    payload.values.bmi = 26.7
    payload.values.basal_metabolic_rate_kcal = 1880.0
    payload.values.skeletal_muscle_kg = 35.6
    payload.values.total_energy_kcal = 3008.0
    payload.values.physical_age = 26
    return payload


class TestImageParseService:
    def test_prefers_openai_provider_when_available(self):
        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_ai_parse_result(),
        ) as mock_parse, patch(
            "app.services.body_composition_image_parse_service._image_ai_available",
            return_value=True,
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=_local_ocr_payload(),
            )

        assert result.values.weight_kg == 84.5
        mock_parse.assert_called_once()

    @patch("app.services.body_composition_image_parse_service._parse_with_claude_vision")
    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_prefers_ai_value_over_bad_local_conflict(self, _mock_available, mock_parse):
        mock_parse.return_value = _ai_parse_result()

        from app.services.body_composition_image_parse_service import parse_body_composition_image

        result = parse_body_composition_image(
            image_bytes=b"fake-image",
            media_type="image/jpeg",
            device_profile="tezewa_receipt_v1",
            local_ocr_result=_local_ocr_payload(),
        )

        assert result.values.weight_kg == 84.5
        assert result.values.body_fat_kg == 19.46
        assert result.values.body_fat_percent == 23.0
        assert result.values.waist_hip_ratio == 0.88
        assert result.values.target_weight_kg == 68.3
        assert result.engine in {"hybrid", "ai_assisted"}
        assert result.fallback_used is (result.engine == "hybrid")

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_removes_stale_local_ai_unavailable_warning_when_ai_succeeds(self, _mock_available):
        stale_local = _local_ocr_payload()
        stale_local.warnings.append(
            BodyCompositionOcrWarning(
                field=None,
                message="Leitura assistida por IA indisponivel; mantivemos a leitura local com revisao manual obrigatoria.",
                severity="warning",
            )
        )

        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_ai_parse_result_with_extra_values(),
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=stale_local,
            )

        assert all("indisponivel" not in warning.message.lower() for warning in result.warnings)
        assert result.confidence > stale_local.confidence

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=True)
    def test_keeps_non_key_local_value_when_only_noisy_local_support_exists(self, _mock_available):
        stale_local = _local_ocr_payload()
        stale_local.values.body_water_kg = 17.7
        stale_local.warnings.append(
            BodyCompositionOcrWarning(
                field="body_water_kg",
                message="body water kg foi inferido pela ordem esperada do recibo. Revisar manualmente.",
                severity="warning",
            )
        )

        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", "test-openai-key"), patch(
            "app.services.body_composition_image_parse_service._parse_with_openai_vision",
            return_value=_ai_parse_result(),
        ):
            from app.services.body_composition_image_parse_service import parse_body_composition_image

            result = parse_body_composition_image(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=stale_local,
            )

        assert result.values.body_water_kg == 17.7

    def test_resolve_image_ai_provider_returns_none_without_keys(self):
        with patch("app.services.body_composition_image_parse_service.settings.openai_api_key", ""), patch(
            "app.services.body_composition_image_parse_service.settings.claude_api_key",
            "",
        ):
            from app.services.body_composition_image_parse_service import _resolve_image_ai_provider

            assert _resolve_image_ai_provider() is None

    @patch("app.services.body_composition_image_parse_service._image_ai_available", return_value=False)
    def test_returns_local_with_warning_when_assisted_read_is_disabled(self, _mock_available):
        from app.services.body_composition_image_parse_service import parse_body_composition_image

        result = parse_body_composition_image(
            image_bytes=b"fake-image",
            media_type="image/png",
            device_profile="tezewa_receipt_v1",
            local_ocr_result=_local_ocr_payload(),
        )

        assert result.engine == "local"
        assert result.fallback_used is False
        assert result.needs_review is True
        assert any("Leitura assistida por IA indisponivel" in warning.message for warning in result.warnings)


class TestImageParseRoute:
    def test_requires_authentication(self, client):
        response = client.post(
            f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
            files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
        )

        assert response.status_code == 401

    def test_respects_current_user_gym_scope(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            def _member_lookup(db, member_id, gym_id):
                assert gym_id == mock_owner.gym_id
                return SimpleNamespace(id=member_id, gym_id=gym_id)

            with patch("app.routers.members.get_member_or_404", side_effect=_member_lookup), patch(
                "app.routers.members.parse_body_composition_image",
                return_value=_ai_parse_result(),
            ):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={"device_profile": "tezewa_receipt_v1"},
                    files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
                )

            assert response.status_code == 200
            assert response.json()["values"]["weight_kg"] == 84.5
        finally:
            app.dependency_overrides.clear()

    def test_rejects_invalid_file_type(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch("app.routers.members.get_member_or_404", return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id)):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={"device_profile": "tezewa_receipt_v1"},
                    files={"file": ("receipt.txt", b"not-an-image", "text/plain")},
                )

            assert response.status_code == 415
            assert "JPEG, PNG ou WEBP" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_returns_local_engine_when_image_ai_is_disabled(self, app, client, mock_owner):
        from tests.conftest import make_mock_db

        mock_db = make_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_owner

        try:
            with patch("app.routers.members.get_member_or_404", return_value=SimpleNamespace(id=MEMBER_ID, gym_id=mock_owner.gym_id)), patch(
                "app.services.body_composition_image_parse_service.settings.body_composition_image_ai_enabled",
                False,
            ):
                response = client.post(
                    f"/api/v1/members/{MEMBER_ID}/body-composition/parse-image",
                    data={
                        "device_profile": "tezewa_receipt_v1",
                        "local_ocr_result": _local_ocr_payload().model_dump_json(),
                    },
                    files={"file": ("receipt.jpg", b"fake-image", "image/jpeg")},
                )

            assert response.status_code == 200
            body = response.json()
            assert body["engine"] == "local"
            assert body["fallback_used"] is False
            assert body["values"]["weight_kg"] == 14.41
            assert any("Leitura assistida por IA indisponivel" in item["message"] for item in body["warnings"])
        finally:
            app.dependency_overrides.clear()

    def test_openai_image_ai_available_does_not_depend_on_claude_breaker(self):
        with patch("app.services.body_composition_image_parse_service.settings.body_composition_image_ai_enabled", True), patch(
            "app.services.body_composition_image_parse_service.settings.openai_api_key",
            "test-openai-key",
        ), patch(
            "app.services.body_composition_image_parse_service.claude_circuit_breaker.is_open",
            return_value=True,
        ):
            from app.services.body_composition_image_parse_service import _image_ai_available

            assert _image_ai_available("openai") is True

    def test_parse_with_openai_vision_uses_json_mode_response(self):
        captured_kwargs = {}

        mock_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"device_model":"Tezewa","values":{"weight_kg":84.5,"body_fat_kg":19.46,"body_fat_percent":23.0,"waist_hip_ratio":0.88},"ranges":{"weight_kg":{"min":61.7,"max":75.5}},"warnings":[],"needs_review":false}'
                    )
                )
            ]
        )
        mock_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: captured_kwargs.update(kwargs) or mock_response,
                )
            )
        )

        with patch("app.services.body_composition_image_parse_service._create_openai_client", return_value=mock_client):
            from app.services.body_composition_image_parse_service import _parse_with_openai_vision

            result = _parse_with_openai_vision(
                image_bytes=b"fake-image",
                media_type="image/jpeg",
                device_profile="tezewa_receipt_v1",
                local_ocr_result=_local_ocr_payload(),
            )

        assert result.values.weight_kg == 84.5
        assert result.values.body_fat_kg == 19.46
        assert result.values.body_fat_percent == 23.0
        assert result.engine == "ai_assisted"
        assert result.fallback_used is False
        prompt = captured_kwargs["messages"][1]["content"][0]["text"]
        assert "Template obrigatorio de values" in prompt
        assert "body_water_percent" in prompt
        assert "target_weight_kg" in prompt
        assert "total_energy_kcal" in prompt
        assert "muscle_control_kg" in prompt
        assert "nao pare nos campos principais" in prompt
