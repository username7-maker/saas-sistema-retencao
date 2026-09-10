from __future__ import annotations

import base64
import json
import logging
import re
import struct
import unicodedata
from datetime import date, datetime
from time import perf_counter
from typing import Any

import anthropic
from fastapi import HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.circuit_breaker import claude_circuit_breaker
from app.core.config import settings
from app.schemas.body_composition import (
    BodyCompositionCaptureMetadata,
    BodyCompositionDeviceProfile,
    BodyCompositionFieldMetadata,
    BodyCompositionImageOcrPayload,
    BodyCompositionImageParseResultRead,
    BodyCompositionImagePreprocessing,
    BodyCompositionImageProcessing,
    BodyCompositionImageQuality,
    BodyCompositionOcrValues,
    BodyCompositionOcrWarning,
    BodyCompositionProfileConflict,
    BodyCompositionRangeValue,
    BodyCompositionValidationIssue,
)
from app.services.body_composition_report_service import (
    build_body_composition_quality_flags,
    calculate_body_water_percent,
)
from app.services.document_image_preprocessing import DocumentPreprocessingResult, preprocess_receipt_image
from app.utils.claude import _parse_claude_json

logger = logging.getLogger(__name__)

SUPPORTED_MEDIA_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
}
MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024
KEY_FIELDS = ("weight_kg", "body_fat_kg", "body_fat_percent", "waist_hip_ratio")
INT_FIELDS = {"age_years", "physical_age", "health_score"}
TEXT_FIELDS = {"measured_at"}
DEMOGRAPHIC_FIELDS = {"age_years", "sex", "height_cm"}
AI_EVIDENCE_CRITICAL_FIELDS = {"weight_kg", "bmi"}
POSITIONAL_INFERENCE_MARKERS = ("inferido pela ordem", "inferida pela ordem", "ordem esperada")
MIN_EVIDENCE_CONFIDENCE = 0.65
RECOVERY_READ_FIELDS = ("age_years", "sex", "height_cm", "weight_kg", "bmi")
FIELD_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "evaluation_date": ("date", "data", "test time", "hora do teste"),
    "measured_at": ("date", "data", "time", "hora"),
    "age_years": ("age", "idade"),
    "sex": ("sex", "sexo", "gender", "genero"),
    "height_cm": ("height", "altura", "estatura"),
    "weight_kg": ("weight", "peso"),
    "body_fat_kg": ("body fat", "gordura corporal", "massa de gordura"),
    "body_fat_percent": ("body fat ratio", "body fat rate", "percentual de gordura", "gordura corporal"),
    "waist_hip_ratio": ("waist-hip", "waist hip", "cintura-quadril", "cintura quadril"),
    "fat_free_mass_kg": (
        "fat-free mass",
        "fat free mass",
        "fat-free weight",
        "fat free weight",
        "fat free",
        "massa livre de gordura",
    ),
    "inorganic_salt_kg": ("inorganic salt", "sal inorganico", "minerais"),
    "muscle_mass_kg": ("muscle mass", "massa muscular"),
    "protein_kg": ("protein", "proteina"),
    "body_water_kg": ("body water", "body moisture", "agua corporal"),
    "lean_mass_kg": ("lean mass", "massa magra"),
    "visceral_fat_level": ("visceral fat", "gordura visceral"),
    "bmi": ("bmi", "imc"),
    "basal_metabolic_rate_kcal": (
        "bmr",
        "basic metabolism",
        "basal metabolism",
        "basal metabolic",
        "metabolic rate",
        "metabolismo basal",
        "tmb",
    ),
    "skeletal_muscle_kg": ("skeletal muscle", "musculo esqueletico", "massa muscular esqueletica"),
    "target_weight_kg": ("target weight", "peso alvo", "peso meta"),
    "weight_control_kg": ("weight control", "controle de peso"),
    "muscle_control_kg": ("muscle control", "controle muscular"),
    "fat_control_kg": ("fat control", "controle de gordura"),
    "total_energy_kcal": ("total energy", "energy consumption", "energia total", "consumo de energia"),
    "physical_age": ("physical age", "idade fisica"),
    "health_score": ("health score", "pontuacao de saude", "score de saude"),
}
NUMERIC_FIELDS = (
    "weight_kg",
    "body_fat_kg",
    "body_fat_percent",
    "waist_hip_ratio",
    "fat_free_mass_kg",
    "inorganic_salt_kg",
    "muscle_mass_kg",
    "protein_kg",
    "body_water_kg",
    "lean_mass_kg",
    "body_water_percent",
    "visceral_fat_level",
    "bmi",
    "basal_metabolic_rate_kcal",
    "skeletal_muscle_kg",
    "target_weight_kg",
    "weight_control_kg",
    "muscle_control_kg",
    "fat_control_kg",
    "total_energy_kcal",
    "physical_age",
    "health_score",
)
FIELD_EXTRACTION_GUIDE: tuple[tuple[str, str], ...] = (
    ("evaluation_date", "data da avaliacao impressa no recibo, em YYYY-MM-DD quando visivel"),
    ("measured_at", "data e hora da avaliacao quando estiverem explicitamente visiveis"),
    ("age_years", "idade em anos, quando impressa"),
    ("sex", "sexo biologico impresso no laudo: male ou female"),
    ("height_cm", "estatura/altura em centimetros"),
    ("weight_kg", "Weight (kg) ou peso atual"),
    ("body_fat_kg", "Body fat (kg)"),
    ("body_fat_percent", "Body fat ratio (%) ou percentual de gordura"),
    ("waist_hip_ratio", "Waist-Hip Ratio"),
    ("fat_free_mass_kg", "Fat-free mass (kg) ou Fat free weight (kg)"),
    ("inorganic_salt_kg", "Inorganic salt (kg)"),
    ("muscle_mass_kg", "Muscle mass (kg)"),
    ("protein_kg", "Protein (kg)"),
    ("body_water_kg", "Body water (kg) ou Body moisture, mesmo quando (kg) estiver na linha anterior"),
    ("lean_mass_kg", "Lean mass (kg), quando existir nessa versao do recibo"),
    ("body_water_percent", "campo derivado pelo sistema; deve permanecer null na extracao"),
    ("visceral_fat_level", "Visceral fat"),
    ("bmi", "BMI"),
    ("basal_metabolic_rate_kcal", "BMR, Basic metabolism ou Basal metabolism (kcal)"),
    ("skeletal_muscle_kg", "Skeletal muscle (kg), ainda que a unidade nao esteja ao lado do rotulo"),
    ("target_weight_kg", "Target weight (kg)"),
    ("weight_control_kg", "Weight control (kg)"),
    ("muscle_control_kg", "Muscle control (kg)"),
    ("fat_control_kg", "Fat control (kg)"),
    ("total_energy_kcal", "Total energy / energy consumption (kcal)"),
    ("physical_age", "Physical age"),
    ("health_score", "Health score"),
)
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "age_years": (1, 119),
    "height_cm": (100, 250),
    "weight_kg": (30, 300),
    "body_fat_kg": (1, 80),
    "body_fat_percent": (2, 75),
    "waist_hip_ratio": (0.5, 1.5),
    "fat_free_mass_kg": (20, 200),
    "inorganic_salt_kg": (1, 10),
    "muscle_mass_kg": (10, 100),
    "protein_kg": (1, 40),
    "body_water_kg": (10, 100),
    "visceral_fat_level": (1, 30),
    "bmi": (10, 80),
    "basal_metabolic_rate_kcal": (500, 4000),
    "skeletal_muscle_kg": (5, 100),
    "target_weight_kg": (30, 300),
    "weight_control_kg": (-100, 100),
    "muscle_control_kg": (-100, 100),
    "fat_control_kg": (-100, 100),
    "total_energy_kcal": (500, 7000),
    "physical_age": (1, 120),
    "health_score": (1, 100),
}


class _BodyCompositionVisionResponse(BaseModel):
    device_model: str | None = None
    values: BodyCompositionOcrValues = Field(default_factory=BodyCompositionOcrValues)
    ranges: dict[str, BodyCompositionRangeValue] = Field(default_factory=dict)
    warnings: list[BodyCompositionOcrWarning] = Field(default_factory=list)
    needs_review: bool = False
    field_metadata: dict[str, BodyCompositionFieldMetadata] = Field(default_factory=dict)


def _build_values_template() -> str:
    template = dict.fromkeys(BodyCompositionOcrValues.model_fields)
    return json.dumps(template, ensure_ascii=False)


def _build_field_guide_text() -> str:
    return "\n".join(f"- {field_name}: {description}" for field_name, description in FIELD_EXTRACTION_GUIDE)


def _build_vision_prompt(
    *,
    device_profile: BodyCompositionDeviceProfile,
    local_ocr_result: BodyCompositionImageOcrPayload | None,
    provider_name: str,
) -> str:
    local_hint = _build_local_hint(local_ocr_result)
    provider_instruction = (
        "Retorne APENAS JSON com chaves: device_model, values, ranges, warnings, needs_review, field_metadata.\n"
        if provider_name == "claude"
        else "Retorne APENAS os campos estruturados solicitados.\n"
    )
    return (
        "Voce extrai dados estruturados de um recibo de bioimpedancia para um sistema de academia.\n"
        "O layout esperado e do perfil tezewa_receipt_v1.\n"
        f"{provider_instruction}"
        "Regras obrigatorias:\n"
        "- use a imagem como fonte de verdade; o OCR local e apenas pista auxiliar\n"
        "- nao invente valores; se estiver em duvida, use null e adicione warning\n"
        "- para CADA valor nao nulo, field_metadata deve conter label, evidence e confidence entre 0 e 1\n"
        "- label e o rotulo exato identificado junto ao numero; evidence e o trecho curto "
        "visivel que sustenta a leitura\n"
        "- suggested_value em field_metadata deve repetir exatamente o valor extraido em values\n"
        "- se label ou evidence nao estiverem legiveis, retorne null em values para esse campo\n"
        "- jamais use Physical age/Idade fisica como age_years; esse rotulo pertence somente a physical_age\n"
        "- Age e Physical age sao campos distintos mesmo quando imprimem o mesmo numero\n"
        "- neste recibo estreito, um rotulo ou sua unidade pode continuar na linha seguinte; una somente linhas "
        "consecutivas que formem um rotulo conhecido, sem associar pela posicao\n"
        "- exemplos do layout: 'Fat free / (kg) / weight' significa fat_free_mass_kg; "
        "'(kg) / Body moisture' significa body_water_kg\n"
        "- 'Basal metabolism' significa basal_metabolic_rate_kcal e 'Skeletal muscle' significa "
        "skeletal_muscle_kg, mesmo sem a unidade impressa ao lado\n"
        "- normalize Man/Male para male e Woman/Female para female\n"
        "- antes de concluir, confira se Weight, Height e BMI impressos obedecem aproximadamente "
        "BMI = Weight / Height_m^2; se um algarismo de qualquer um desses tres campos estiver visualmente "
        "ambiguo (por exemplo 3/6 ou 5/6), reinspecione o glifo na imagem e use a coerencia apenas para "
        "desempatar uma leitura visual plausivel; "
        "nunca fabrique ou corrija um valor somente pela formula\n"
        "- percorra todo o recibo; nao pare nos campos principais e cubra composicao corporal, "
        "metabolismo, comprehensive evaluation e controles\n"
        "- values deve conter TODAS as chaves esperadas do sistema, mesmo quando o valor for null\n"
        "- diferencie obrigatoriamente body_fat_kg de body_fat_percent\n"
        "- body_fat_kg corresponde a 'Body fat (kg)'\n"
        "- body_fat_percent corresponde a 'Body fat ratio (%)'\n"
        "- body_water_kg corresponde a 'Body moisture'/'Body water' em kg\n"
        "- body_water_percent NAO deve ser inferido, calculado ou copiado pela IA; retorne sempre null\n"
        "- o sistema calcula body_water_percent deterministicamente usando body_water_kg / weight_kg * 100\n"
        "- skeletal_muscle_kg e muscle_mass_kg sao campos diferentes e podem coexistir\n"
        "- preserve valores negativos em weight_control_kg, muscle_control_kg e fat_control_kg\n"
        "- physical_age e health_score devem ser inteiros quando visiveis\n"
        "- quando houver faixa impressa, preencha ranges com min/max\n"
        "- warnings deve ser lista de objetos com field, message, severity (warning|critical)\n"
        "- evaluation_date so deve ser preenchida se estiver realmente visivel na imagem\n"
        f"- device_profile atual: {device_profile}\n"
        "Campos esperados em values:\n"
        f"{_build_field_guide_text()}\n"
        f"Template obrigatorio de values: {_build_values_template()}\n"
        "Formato de field_metadata: {\"weight_kg\": {\"origin\": \"ai_image\", "
        "\"state\": \"accepted\", \"confidence\": 0.98, \"label\": \"Weight (kg)\", "
        "\"evidence\": \"Weight (kg) 84.5\", \"suggested_value\": 84.5}}\n"
        f"- dica opcional do OCR local: {json.dumps(local_hint, ensure_ascii=False)}\n"
        "Responda em portugues do Brasil."
    )


def parse_body_composition_image(
    *,
    image_bytes: bytes,
    media_type: str | None,
    device_profile: str,
    local_ocr_result: BodyCompositionImageOcrPayload | None = None,
    evaluation_date: date | None = None,
    member_birthdate: date | None = None,
    member_sex: str | None = None,
    member_height_cm: Any = None,
    previous_weight_kg: Any = None,
    capture_metadata: BodyCompositionCaptureMetadata | None = None,
    supplemental_images: list[tuple[bytes, str | None]] | None = None,
) -> BodyCompositionImageParseResultRead:
    started_at = perf_counter()
    normalized_device_profile = _normalize_device_profile(device_profile)
    normalized_media_type = _validate_image_payload(image_bytes, media_type)
    provider = _resolve_image_ai_provider()
    image_width, image_height = _read_image_dimensions(image_bytes, normalized_media_type)
    input_images = [(image_bytes, normalized_media_type)]
    for supplemental_bytes, supplemental_media_type in supplemental_images or []:
        input_images.append((supplemental_bytes, _validate_image_payload(supplemental_bytes, supplemental_media_type)))
    if len(input_images) > 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie no maximo tres imagens.")
    preprocessings = [
        preprocess_receipt_image(content, enabled=settings.bioimpedance_scanner_v2)
        for content, _media_type in input_images
    ]
    preprocessing = preprocessings[0]
    segment_roles = ["full"] if len(input_images) == 1 else ["top", "middle", "bottom"][:len(input_images)]
    provider_images = []
    recovery_provider_images = []
    has_recovery_variant = False
    for index, ((content, normalized_type), prepared) in enumerate(zip(input_images, preprocessings, strict=True)):
        provider_images.append((
            prepared.image_bytes if prepared and prepared.applied else content,
            prepared.media_type if prepared and prepared.applied else normalized_type,
            segment_roles[index],
        ))
        recovery_bytes = prepared.recovery_image_bytes if prepared else None
        recovery_type = prepared.recovery_media_type if prepared else None
        has_recovery_variant = has_recovery_variant or recovery_bytes is not None
        recovery_provider_images.append((
            recovery_bytes or (prepared.image_bytes if prepared and prepared.applied else content),
            recovery_type or (prepared.media_type if prepared and prepared.applied else normalized_type),
            segment_roles[index],
        ))

    local_payload = (
        BodyCompositionImageOcrPayload.model_validate(local_ocr_result.model_dump()) if local_ocr_result else None
    )

    if not _image_ai_available(provider):
        result = _build_local_only_result(
            local_payload,
            "Leitura assistida por IA indisponivel; mantivemos a leitura local com revisao manual obrigatoria.",
            normalized_device_profile,
        )
        if settings.body_composition_image_ai_validation_enabled:
            result = _validate_ai_first_result(
                result,
                extraction_origin="local_ocr",
                evaluation_date=evaluation_date,
                member_birthdate=member_birthdate,
                member_sex=member_sex,
                member_height_cm=member_height_cm,
                previous_weight_kg=previous_weight_kg,
            )
        return _complete_parse_request(
            result,
            started_at=started_at,
            provider=provider,
            image_width=image_width,
            image_height=image_height,
            preprocessing=preprocessing,
            capture_metadata=capture_metadata,
        )

    enhancement_retry_used = False
    enhancement_variant = None
    try:
        provider_local_hint = (
            None if settings.body_composition_image_ai_validation_enabled else local_payload
        )
        if provider == "openai":
            ai_payload = _parse_with_openai_vision(
                images=provider_images,
                device_profile=normalized_device_profile,
                local_ocr_result=provider_local_hint,
            )
        else:
            ai_payload = _parse_with_claude_vision(
                images=provider_images,
                device_profile=normalized_device_profile,
                local_ocr_result=provider_local_hint,
            )
        missing_recovery_fields = _missing_recovery_read_fields(ai_payload)
        if has_recovery_variant and missing_recovery_fields:
            try:
                if provider == "openai":
                    recovery_payload = _parse_with_openai_vision(
                        images=recovery_provider_images,
                        device_profile=normalized_device_profile,
                        local_ocr_result=provider_local_hint,
                    )
                else:
                    recovery_payload = _parse_with_claude_vision(
                        images=recovery_provider_images,
                        device_profile=normalized_device_profile,
                        local_ocr_result=provider_local_hint,
                    )
                ai_payload = _merge_ai_recovery_result(ai_payload, recovery_payload)
                enhancement_retry_used = True
                enhancement_variant = "thermal_adaptive_threshold+unsharp"
                logger.info(
                    "body_composition_image_enhancement_retry provider=%s missing_fields=%s",
                    provider,
                    ",".join(missing_recovery_fields),
                )
            except Exception as recovery_exc:
                # The primary AI result remains valid. A recovery failure must
                # never turn a partially successful read into a total failure.
                logger.warning(
                    "body_composition_image_enhancement_retry_failed provider=%s error_type=%s",
                    provider,
                    type(recovery_exc).__name__,
                )
        if provider == "claude":
            claude_circuit_breaker.record_success()
    except Exception as exc:
        if provider == "claude":
            claude_circuit_breaker.record_failure()
        failure_message, failure_severity = _classify_assisted_read_failure(exc)
        logger.warning(
            "body_composition_image_ai_failed provider=%s error_type=%s local_fallback=%s",
            provider or "unavailable",
            type(exc).__name__,
            local_payload is not None,
        )
        result = _build_local_only_result(
            local_payload,
            failure_message,
            normalized_device_profile,
            severity=failure_severity,
        )
        if settings.body_composition_image_ai_validation_enabled:
            result = _validate_ai_first_result(
                result,
                extraction_origin="local_ocr",
                evaluation_date=evaluation_date,
                member_birthdate=member_birthdate,
                member_sex=member_sex,
                member_height_cm=member_height_cm,
                previous_weight_kg=previous_weight_kg,
            )
        return _complete_parse_request(
            result,
            started_at=started_at,
            provider=provider,
            image_width=image_width,
            image_height=image_height,
            preprocessing=preprocessing,
            capture_metadata=capture_metadata,
        )

    if settings.body_composition_image_ai_validation_enabled:
        result = _validate_ai_first_result(
            ai_payload,
            extraction_origin="ai_image",
            evaluation_date=evaluation_date,
            member_birthdate=member_birthdate,
            member_sex=member_sex,
            member_height_cm=member_height_cm,
            previous_weight_kg=previous_weight_kg,
        )
    else:
        result = _merge_parse_results(local_payload, ai_payload)
    return _complete_parse_request(
        result,
        started_at=started_at,
        provider=provider,
        image_width=image_width,
        image_height=image_height,
        preprocessing=preprocessing,
        capture_metadata=capture_metadata,
        enhancement_retry_used=enhancement_retry_used,
        enhancement_variant=enhancement_variant,
    )


def _resolve_image_ai_provider() -> str | None:
    if settings.openai_api_key:
        return "openai"
    if settings.claude_api_key:
        return "claude"
    return None


def _create_openai_client(*, timeout_seconds: int | None = None) -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=timeout_seconds or settings.openai_timeout_seconds,
        max_retries=0,
    )


def _parse_with_openai_vision(
    *,
    images: list[tuple[bytes, str, str]] | None = None,
    image_bytes: bytes | None = None,
    media_type: str | None = None,
    device_profile: BodyCompositionDeviceProfile,
    local_ocr_result: BodyCompositionImageOcrPayload | None,
) -> BodyCompositionImageParseResultRead:
    # Keep the original single-image callable contract for internal callers and
    # focused tests while accepting the new segmented capture contract.
    if images is None:
        if image_bytes is None:
            raise ValueError("Uma imagem e obrigatoria para a leitura assistida.")
        images = [(image_bytes, media_type or "image/jpeg", "full")]
    prompt = _build_vision_prompt(
        device_profile=device_profile,
        local_ocr_result=local_ocr_result,
        provider_name="openai",
    )
    if len(images) > 1:
        prompt += (
            "\nAs imagens representam topo, centro e rodape do mesmo recibo. "
            "Use o topo para Age/Sex/Height/Weight/Test time, o centro para Body composition e o rodape "
            "para Body parameters/Comprehensive evaluation. Valores repetidos devem concordar; em conflito, "
            "marque revisao. Informe field_metadata.segment para todo campo extraido."
        )

    client = _create_openai_client(timeout_seconds=settings.body_composition_image_ai_timeout_seconds)
    image_content: list[dict[str, Any]] = []
    for image_bytes, media_type, role in images:
        image_content.extend([
            {"type": "text", "text": f"Imagem do segmento: {role}."},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}",
                    "detail": "high",
                },
            },
        ])
    response = client.chat.completions.create(
        model=settings.openai_vision_model,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "body_composition_receipt",
                "strict": False,
                "schema": _BodyCompositionVisionResponse.model_json_schema(),
            },
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "Extraia os dados estruturados de bioimpedancia com alta precisao e sem inventar valores. "
                    "Responda somente JSON valido."
                ),
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}, *image_content],
            },
        ],
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise RuntimeError("OpenAI nao retornou payload estruturado para a leitura assistida.")
    parsed = _parse_claude_json(content)
    return _normalize_ai_payload(parsed, device_profile=device_profile, local_ocr_result=local_ocr_result)


def _parse_with_claude_vision(
    *,
    images: list[tuple[bytes, str, str]] | None = None,
    image_bytes: bytes | None = None,
    media_type: str | None = None,
    device_profile: BodyCompositionDeviceProfile,
    local_ocr_result: BodyCompositionImageOcrPayload | None,
) -> BodyCompositionImageParseResultRead:
    if images is None:
        if image_bytes is None:
            raise ValueError("Uma imagem e obrigatoria para a leitura assistida.")
        images = [(image_bytes, media_type or "image/jpeg", "full")]
    prompt = _build_vision_prompt(
        device_profile=device_profile,
        local_ocr_result=local_ocr_result,
        provider_name="claude",
    )
    if len(images) > 1:
        prompt += (
            "\nAs imagens representam topo, centro e rodape do mesmo recibo. "
            "Use o topo para Age/Sex/Height/Weight/Test time, o centro para Body composition e o rodape "
            "para Body parameters/Comprehensive evaluation. Valores repetidos devem concordar; em conflito, "
            "marque revisao. Informe field_metadata.segment para todo campo extraido."
        )
    prompt = (
        f"{prompt}\n"
        "JSON esperado:\n"
        "{"
        "\"device_model\": \"Tezewa ou null\", "
        "\"values\": "
        f"{_build_values_template()}, "
        "\"ranges\": {\"weight_kg\": {\"min\": 61.7, \"max\": 75.5}}, "
        "\"field_metadata\": {\"weight_kg\": {\"origin\": \"ai_image\", \"state\": \"accepted\", "
        "\"confidence\": 0.98, \"label\": \"Weight (kg)\", \"evidence\": \"Weight (kg) 84.5\", "
        "\"suggested_value\": 84.5}}, "
        "\"warnings\": [], "
        "\"needs_review\": false"
        "}\n"
    )

    client = anthropic.Anthropic(
        api_key=settings.claude_api_key,
        timeout=settings.body_composition_image_ai_timeout_seconds,
    )
    image_content: list[dict[str, Any]] = []
    for image_bytes, media_type, role in images:
        image_content.extend([
            {"type": "text", "text": f"Imagem do segmento: {role}."},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                },
            },
        ])
    response = client.messages.create(
        model=settings.claude_vision_model or settings.claude_model,
        max_tokens=max(settings.claude_max_tokens, 900),
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}, *image_content],
            }
        ],
    )
    response_text = "\n".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ).strip()
    parsed = _parse_claude_json(response_text)
    return _normalize_ai_payload(parsed, device_profile=device_profile, local_ocr_result=local_ocr_result)


def _normalize_ai_payload(
    payload: dict[str, Any],
    *,
    device_profile: BodyCompositionDeviceProfile,
    local_ocr_result: BodyCompositionImageOcrPayload | None,
) -> BodyCompositionImageParseResultRead:
    values_source = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    ranges_source = payload.get("ranges")
    warnings_source = payload.get("warnings")
    metadata_source = payload.get("field_metadata")

    normalized_values = _normalize_values(values_source)
    normalized_values["body_water_percent"] = None
    values = BodyCompositionOcrValues.model_validate(normalized_values)
    ranges = _normalize_ranges(ranges_source)
    ranges.pop("body_water_percent", None)
    warnings = [
        warning
        for warning in _normalize_warnings(warnings_source)
        if warning.field != "body_water_percent"
    ]
    field_metadata = _normalize_field_metadata(metadata_source)
    field_metadata.pop("body_water_percent", None)
    confidence = _initial_ai_confidence(values, field_metadata)

    return BodyCompositionImageParseResultRead(
        device_profile=device_profile,
        device_model=_normalize_string(payload.get("device_model"))
        or (local_ocr_result.device_model if local_ocr_result else None),
        values=values,
        ranges=ranges,
        warnings=warnings,
        confidence=confidence,
        raw_text=local_ocr_result.raw_text if local_ocr_result else "",
        needs_review=bool(payload.get("needs_review", False)),
        engine="ai_assisted",
        fallback_used=False,
        field_metadata=field_metadata,
        validation_issues=[],
    )


def _missing_recovery_read_fields(result: BodyCompositionImageParseResultRead) -> list[str]:
    return [field_name for field_name in RECOVERY_READ_FIELDS if getattr(result.values, field_name, None) is None]


def _merge_ai_recovery_result(
    primary: BodyCompositionImageParseResultRead,
    recovery: BodyCompositionImageParseResultRead,
) -> BodyCompositionImageParseResultRead:
    """Fill only absent values from the recovery read; never replace a primary value."""
    value_updates: dict[str, Any] = {}
    recovered_fields: set[str] = set()
    for field_name in BodyCompositionOcrValues.model_fields:
        if getattr(primary.values, field_name, None) is not None:
            continue
        recovered_value = getattr(recovery.values, field_name, None)
        if recovered_value is None:
            continue
        value_updates[field_name] = recovered_value
        recovered_fields.add(field_name)

    ranges = dict(primary.ranges)
    for field_name, range_value in recovery.ranges.items():
        ranges.setdefault(field_name, range_value)

    field_metadata = dict(primary.field_metadata)
    for field_name in recovered_fields:
        metadata = recovery.field_metadata.get(field_name)
        if metadata is not None:
            field_metadata[field_name] = metadata

    recovery_warnings = [
        warning for warning in recovery.warnings if warning.field is None or warning.field in recovered_fields
    ]
    return primary.model_copy(
        update={
            "device_model": primary.device_model or recovery.device_model,
            "values": primary.values.model_copy(update=value_updates),
            "ranges": ranges,
            "warnings": _dedupe_warnings([*primary.warnings, *recovery_warnings]),
            "field_metadata": field_metadata,
            "confidence": max(primary.confidence, recovery.confidence),
            "needs_review": primary.needs_review or recovery.needs_review,
        }
    )


def _merge_parse_results(
    local_result: BodyCompositionImageOcrPayload | None,
    ai_result: BodyCompositionImageParseResultRead,
) -> BodyCompositionImageParseResultRead:
    if local_result is None:
        return _finalize_parse_result(ai_result)

    merged_values = BodyCompositionOcrValues()
    merged_ranges: dict[str, BodyCompositionRangeValue] = {}
    warnings: list[BodyCompositionOcrWarning] = []
    field_metadata: dict[str, BodyCompositionFieldMetadata] = {}
    ai_used_fields: set[str] = set()
    local_used_fields: set[str] = set()

    for field_name in BodyCompositionOcrValues.model_fields:
        ai_value = getattr(ai_result.values, field_name, None)
        local_value = getattr(local_result.values, field_name, None)
        local_field_warnings = _warnings_for_field(local_result.warnings, field_name)
        source = _choose_value_source(field_name, ai_value, local_value, local_field_warnings)
        chosen_value = ai_value if source == "ai" else local_value if source == "local" else None
        setattr(merged_values, field_name, chosen_value)

        if source == "ai":
            ai_used_fields.add(field_name)
            if field_name in ai_result.field_metadata:
                field_metadata[field_name] = ai_result.field_metadata[field_name]
            warnings.extend(_warnings_for_field(ai_result.warnings, field_name))
            if (
                local_value is not None
                and ai_value is not None
                and not _values_close(field_name, ai_value, local_value)
            ):
                warnings.append(
                    BodyCompositionOcrWarning(
                        field=field_name,
                        message=f"{field_name} do OCR local foi substituido pela leitura assistida da imagem.",
                        severity="warning",
                    )
                )
        elif source == "local":
            local_used_fields.add(field_name)
            field_metadata[field_name] = BodyCompositionFieldMetadata(
                origin="local_ocr",
                state="suggested" if local_field_warnings else "accepted",
                confidence=local_result.confidence,
                evidence=None,
            )
            warnings.extend(_warnings_for_field(local_result.warnings, field_name))
            if ai_value is None and local_value is not None and field_name in KEY_FIELDS:
                warnings.append(
                    BodyCompositionOcrWarning(
                        field=field_name,
                        message=f"Leitura assistida nao confirmou {field_name}; mantivemos o OCR local.",
                        severity="warning",
                    )
                )

        chosen_range = _choose_range(ai_result.ranges.get(field_name), local_result.ranges.get(field_name))
        if chosen_range:
            merged_ranges[field_name] = chosen_range

    warnings.extend(_warnings_for_field(ai_result.warnings, None))
    warnings.extend(_warnings_for_field_without_local_ai_fallback(local_result.warnings, None))

    engine = "hybrid" if ai_used_fields and local_used_fields else "ai_assisted" if ai_used_fields else "local"
    confidence = _compute_confidence(
        engine=engine,
        warnings=warnings,
        ai_used_count=len(ai_used_fields),
        local_used_count=len(local_used_fields),
        local_confidence=ai_result.confidence,
    )

    return _finalize_parse_result(
        BodyCompositionImageParseResultRead(
            device_profile=ai_result.device_profile,
            device_model=ai_result.device_model or local_result.device_model,
            values=merged_values,
            ranges=merged_ranges,
            warnings=warnings,
            confidence=confidence,
            raw_text=local_result.raw_text,
            needs_review=ai_result.needs_review or local_result.needs_review,
            engine=engine,
            fallback_used=engine == "hybrid",
            field_metadata=field_metadata,
            validation_issues=list(ai_result.validation_issues),
        )
    )


def _build_local_only_result(
    local_result: BodyCompositionImageOcrPayload | None,
    message: str,
    device_profile: BodyCompositionDeviceProfile,
    *,
    severity: str = "warning",
) -> BodyCompositionImageParseResultRead:
    if local_result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Leitura assistida indisponivel e nenhum OCR local foi fornecido.",
        )

    warnings = list(local_result.warnings)
    warnings.append(BodyCompositionOcrWarning(field=None, message=message, severity=severity))
    return _finalize_parse_result(
        BodyCompositionImageParseResultRead(
            device_profile=device_profile,
            device_model=local_result.device_model,
            values=local_result.values,
            ranges=local_result.ranges,
            warnings=warnings,
            confidence=max(0.2, round(min(local_result.confidence, 0.72), 2)),
            raw_text=local_result.raw_text,
            needs_review=True,
            engine="local",
            fallback_used=False,
            field_metadata={
                field_name: BodyCompositionFieldMetadata(
                    origin="local_ocr",
                    state="suggested" if _warnings_for_field(warnings, field_name) else "accepted",
                    confidence=local_result.confidence,
                )
                for field_name in BodyCompositionOcrValues.model_fields
                if getattr(local_result.values, field_name, None) is not None
            },
        )
    )


def _finalize_parse_result(result: BodyCompositionImageParseResultRead) -> BodyCompositionImageParseResultRead:
    values = result.values.model_copy(
        update={
            "body_water_percent": calculate_body_water_percent(
                weight_kg=result.values.weight_kg,
                body_water_kg=result.values.body_water_kg,
            )
        }
    )


    ranges = dict(result.ranges)
    ranges.pop("body_water_percent", None)
    deduped_warnings = _dedupe_warnings(
        [warning for warning in result.warnings if warning.field != "body_water_percent"]
    )
    field_metadata = dict(result.field_metadata)
    if values.body_water_percent is not None:
        field_metadata["body_water_percent"] = BodyCompositionFieldMetadata(
            origin="derived",
            state="accepted",
            confidence=1.0,
        )
    if settings.body_composition_image_ai_validation_enabled:
        confidence = result.confidence
        needs_review = any(issue.severity == "critical" for issue in result.validation_issues)
    else:
        needs_review = (
            any(item.severity == "critical" for item in deduped_warnings)
            or result.needs_review
            or result.confidence < 0.85
        )
        confidence = _compute_confidence(
            engine=result.engine,
            warnings=deduped_warnings,
            ai_used_count=sum(1 for field in KEY_FIELDS if getattr(result.values, field, None) is not None),
            local_used_count=0,
            local_confidence=result.confidence,
            preserve_baseline=result.engine == "local",
        )
    return BodyCompositionImageParseResultRead(
        device_profile=result.device_profile,
        device_model=result.device_model,
        values=values,
        ranges=ranges,
        warnings=deduped_warnings,
        flags=build_body_composition_quality_flags(
            values,
            parsing_confidence=confidence,
            needs_review=needs_review,
        ),
        confidence=confidence,
        raw_text=result.raw_text,
        needs_review=needs_review,
        engine=result.engine,
        fallback_used=result.fallback_used,
        field_metadata=field_metadata,
        validation_issues=result.validation_issues,
        processing=result.processing,
    )


def _validate_ai_first_result(
    result: BodyCompositionImageParseResultRead,
    *,
    extraction_origin: str,
    evaluation_date: date | None,
    member_birthdate: date | None,
    member_sex: str | None,
    member_height_cm: Any,
    previous_weight_kg: Any,
) -> BodyCompositionImageParseResultRead:
    """Apply deterministic safeguards without sending member data to the AI provider."""
    values = result.values.model_copy(deep=True)
    field_metadata = dict(result.field_metadata)
    issues = list(result.validation_issues)
    warnings = list(result.warnings)
    for warning in warnings:
        if warning.severity != "critical":
            continue
        _append_issue(
            issues,
            code="ai_provider_critical_warning" if extraction_origin == "ai_image" else "local_ocr_critical_warning",
            severity="critical",
            fields=[warning.field] if warning.field else [],
            message=warning.message,
        )

    if extraction_origin == "ai_image":
        _discard_unsupported_ai_values(values, field_metadata, issues)
    else:
        _discard_positional_local_values(values, field_metadata, warnings, issues)
        for field_name in BodyCompositionOcrValues.model_fields:
            if getattr(values, field_name, None) is None:
                continue
            field_metadata.setdefault(
                field_name,
                BodyCompositionFieldMetadata(
                    origin="local_ocr",
                    state="suggested",
                    confidence=result.confidence,
                ),
            )

    selected_date = evaluation_date or _parse_date(values.evaluation_date) or date.today()
    if evaluation_date is None:
        _append_issue(
            issues,
            code="evaluation_date_not_provided",
            severity="warning",
            fields=["evaluation_date"],
            message="A data da avaliacao nao foi enviada; confirme a data antes de salvar.",
        )
    values.evaluation_date = selected_date.isoformat()
    field_metadata["evaluation_date"] = BodyCompositionFieldMetadata(
        origin="manual" if evaluation_date is not None else "derived",
        state="accepted" if evaluation_date is not None else "suggested",
        confidence=1.0 if evaluation_date is not None else 0.7,
    )

    _apply_canonical_age(
        values,
        field_metadata,
        issues,
        member_birthdate=member_birthdate,
        evaluation_date=selected_date,
    )
    _apply_canonical_sex(values, field_metadata, issues, member_sex=member_sex)
    _apply_canonical_height(values, field_metadata, issues, member_height_cm=member_height_cm)
    _validate_bmi_consistency(values, field_metadata, issues)
    _validate_previous_weight(values, field_metadata, issues, previous_weight_kg=previous_weight_kg)

    for field_name in BodyCompositionOcrValues.model_fields:
        field_metadata.setdefault(
            field_name,
            BodyCompositionFieldMetadata(
                origin="ai_image" if extraction_origin == "ai_image" else "local_ocr",
                state="unavailable",
            ),
        )

    warnings.extend(_issues_as_legacy_warnings(issues))
    critical = any(issue.severity == "critical" for issue in issues)
    confidence = _validated_confidence(field_metadata, issues)
    validated = result.model_copy(
        update={
            "values": values,
            "warnings": _dedupe_warnings(warnings),
            "confidence": confidence,
            "needs_review": critical,
            "field_metadata": field_metadata,
            "validation_issues": _dedupe_issues(issues),
        }
    )
    return _finalize_parse_result(validated)


def _discard_unsupported_ai_values(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
) -> None:
    for field_name in BodyCompositionOcrValues.model_fields:
        value = getattr(values, field_name, None)
        if value is None or field_name == "body_water_percent":
            continue
        metadata = field_metadata.get(field_name)
        label = (metadata.label or "").strip() if metadata else ""
        evidence = (metadata.evidence or "").strip() if metadata else ""
        if not _is_plausible(field_name, value):
            setattr(values, field_name, None)
            field_metadata[field_name] = BodyCompositionFieldMetadata(
                origin="ai_image",
                state="unavailable",
                confidence=metadata.confidence if metadata else None,
                label=label or None,
                evidence=evidence or None,
            )
            _append_issue(
                issues,
                code="ai_value_out_of_range",
                severity="critical" if field_name in AI_EVIDENCE_CRITICAL_FIELDS else "warning",
                fields=[field_name],
                message=f"{field_name} foi descartado porque esta fora da faixa aceita.",
            )
            continue
        age_uses_physical_label = field_name == "age_years" and _is_physical_age_label(label, evidence)
        if age_uses_physical_label:
            setattr(values, field_name, None)
            field_metadata[field_name] = BodyCompositionFieldMetadata(
                origin="ai_image",
                state="conflict",
                confidence=metadata.confidence if metadata else None,
                label=label or None,
                evidence=evidence or None,
                suggested_value=value,
            )
            _append_issue(
                issues,
                code="physical_age_used_as_chronological_age",
                severity="critical",
                fields=["age_years", "physical_age"],
                message="Idade fisica nao pode ser usada como idade cronologica.",
            )
            continue
        metadata_error = _ai_metadata_validation_error(field_name, value, metadata)
        if metadata_error is not None:
            setattr(values, field_name, None)
            field_metadata[field_name] = BodyCompositionFieldMetadata(
                origin="ai_image",
                state="unavailable",
                confidence=metadata.confidence if metadata else None,
                label=label or None,
                evidence=evidence or None,
            )
            _append_issue(
                issues,
                code=metadata_error,
                severity="critical" if field_name in AI_EVIDENCE_CRITICAL_FIELDS else "warning",
                fields=[field_name],
                message=f"{field_name} foi descartado porque a evidencia da imagem nao confirmou o valor.",
            )
            continue
        confidence = metadata.confidence if metadata and metadata.confidence is not None else 0.0
        state = "accepted" if confidence >= MIN_EVIDENCE_CONFIDENCE else "suggested"
        field_metadata[field_name] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state=state,
            confidence=confidence,
            label=label,
            evidence=evidence,
            suggested_value=value,
        )
        if state == "suggested":
            _append_issue(
                issues,
                code="ai_field_low_confidence",
                severity="critical" if field_name in AI_EVIDENCE_CRITICAL_FIELDS else "warning",
                fields=[field_name],
                message=f"A leitura de {field_name} possui baixa confianca e precisa ser conferida.",
            )


def _ai_metadata_validation_error(
    field_name: str,
    value: Any,
    metadata: BodyCompositionFieldMetadata | None,
) -> str | None:
    if metadata is None or not metadata.label or not metadata.evidence:
        return "ai_value_without_evidence"
    if not _label_matches_field(field_name, metadata.label, metadata.evidence):
        return "ai_label_field_mismatch"
    if not _metadata_value_matches(field_name, value, metadata.suggested_value):
        return "ai_metadata_value_mismatch"
    if not _evidence_supports_value(field_name, value, metadata.evidence):
        return "ai_evidence_value_mismatch"
    return None


def _label_matches_field(field_name: str, label: str, evidence: str = "") -> bool:
    normalized = _normalize_label_text(label)
    normalized_with_evidence = _normalize_label_text(f"{label} {evidence}")
    aliases = FIELD_LABEL_ALIASES.get(field_name)
    if not aliases or not any(alias in normalized_with_evidence for alias in aliases):
        return False
    if field_name == "age_years" and any(marker in normalized for marker in ("physical", "fisica", "metabolic")):
        return False
    if field_name == "physical_age" and not any(marker in normalized for marker in ("physical", "fisica")):
        return False
    if field_name == "muscle_mass_kg" and "skeletal" in normalized:
        return False
    if field_name == "body_fat_kg" and "%" in normalized_with_evidence:
        return False
    if field_name == "body_fat_percent" and not any(
        marker in normalized_with_evidence for marker in ("%", "percent", "ratio", "taxa")
    ):
        return False
    return True


def _metadata_value_matches(field_name: str, value: Any, metadata_value: Any) -> bool:
    if metadata_value is None:
        return False
    if field_name == "evaluation_date":
        return _normalize_date_string(value) == _normalize_date_string(metadata_value)
    if field_name == "measured_at":
        return _normalize_datetime_string(value) == _normalize_datetime_string(metadata_value)
    if field_name == "sex":
        return _normalize_sex_value(value) == _normalize_sex_value(metadata_value)
    return _values_close(field_name, value, metadata_value)


def _evidence_supports_value(field_name: str, value: Any, evidence: str) -> bool:
    if field_name == "evaluation_date":
        target = _normalize_date_string(value)
        date_tokens = re.findall(r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}", evidence)
        return bool(target and any(_normalize_date_string(token) == target for token in date_tokens))
    if field_name == "measured_at":
        normalized = _normalize_datetime_string(value)
        return bool(normalized and normalized[:10] in evidence.replace("/", "-"))
    if field_name == "sex":
        normalized_sex = _normalize_sex_value(value)
        normalized_evidence = _normalize_label_text(evidence)
        expected = (
            ("male", "man", "masculino", "homem")
            if normalized_sex == "male"
            else ("female", "woman", "feminino", "mulher")
        )
        return any(alias in normalized_evidence for alias in expected)

    expected_value = _coerce_float(value)
    if expected_value is None:
        return False
    numeric_tokens = re.findall(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?", evidence)
    return any(
        candidate is not None and _values_close(field_name, expected_value, candidate)
        for token in numeric_tokens
        if (candidate := _coerce_float(token)) is not None
    )


def _normalize_label_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character)).lower().strip()


def _discard_positional_local_values(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    warnings: list[BodyCompositionOcrWarning],
    issues: list[BodyCompositionValidationIssue],
) -> None:
    for warning in warnings:
        message = (warning.message or "").lower()
        if not warning.field or not any(marker in message for marker in POSITIONAL_INFERENCE_MARKERS):
            continue
        if warning.field not in BodyCompositionOcrValues.model_fields:
            continue
        setattr(values, warning.field, None)
        field_metadata[warning.field] = BodyCompositionFieldMetadata(
            origin="local_ocr",
            state="unavailable",
        )
        _append_issue(
            issues,
            code="local_positional_inference_discarded",
            severity="warning",
            fields=[warning.field],
            message=f"{warning.field} foi descartado porque dependia apenas da posicao no recibo.",
        )


def _apply_canonical_age(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
    *,
    member_birthdate: date | None,
    evaluation_date: date,
) -> None:
    photo_age = values.age_years
    photo_metadata = field_metadata.get("age_years")
    canonical_age = _age_on_date(member_birthdate, evaluation_date)
    if canonical_age is None:
        if (
            photo_age is not None
            and photo_metadata is not None
            and photo_metadata.origin == "ai_image"
            and photo_metadata.state == "accepted"
        ):
            values.age_years = photo_age
            field_metadata["age_years"] = _canonical_metadata_with_suggestion(
                origin="ai_image",
                state="accepted",
                photo_metadata=photo_metadata,
                suggested_value=photo_age,
                confidence=photo_metadata.confidence,
            )
            return
        values.age_years = None
        field_metadata["age_years"] = _canonical_metadata_with_suggestion(
            origin="manual",
            state="conflict",
            photo_metadata=photo_metadata,
            suggested_value=photo_age,
        )
        _append_issue(
            issues,
            code="age_manual_confirmation_required",
            severity="critical",
            fields=["age_years"],
            message="Cadastre a data de nascimento ou confirme a idade manualmente.",
        )
        return

    values.age_years = canonical_age
    state = "accepted"
    if photo_age is not None and photo_age != canonical_age:
        state = "conflict"
        _append_issue(
            issues,
            code="age_profile_conflict",
            severity="critical",
            fields=["age_years"],
            message="A idade lida na foto diverge da idade calculada pela data de nascimento.",
        )
    field_metadata["age_years"] = _canonical_metadata_with_suggestion(
        origin="derived",
        state=state,
        photo_metadata=photo_metadata,
        suggested_value=photo_age,
        confidence=1.0,
    )


def _apply_canonical_sex(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
    *,
    member_sex: str | None,
) -> None:
    photo_sex = _normalize_sex_value(values.sex)
    photo_metadata = field_metadata.get("sex")
    canonical_sex = _normalize_sex_value(member_sex)
    if canonical_sex is None:
        if (
            photo_sex is not None
            and photo_metadata is not None
            and photo_metadata.origin == "ai_image"
            and photo_metadata.state == "accepted"
        ):
            values.sex = photo_sex
            field_metadata["sex"] = _canonical_metadata_with_suggestion(
                origin="ai_image",
                state="accepted",
                photo_metadata=photo_metadata,
                suggested_value=photo_sex,
                confidence=photo_metadata.confidence,
            )
            return
        values.sex = None
        field_metadata["sex"] = _canonical_metadata_with_suggestion(
            origin="manual",
            state="conflict",
            photo_metadata=photo_metadata,
            suggested_value=photo_sex,
        )
        _append_issue(
            issues,
            code="sex_manual_confirmation_required",
            severity="critical",
            fields=["sex"],
            message="O sexo para calculo nao esta definido no cadastro e precisa ser confirmado.",
        )
        return

    values.sex = canonical_sex
    state = "accepted"
    if photo_sex is not None and photo_sex != canonical_sex:
        state = "conflict"
        _append_issue(
            issues,
            code="sex_profile_conflict",
            severity="critical",
            fields=["sex"],
            message="O sexo identificado na foto diverge do cadastro do aluno.",
        )
    field_metadata["sex"] = _canonical_metadata_with_suggestion(
        origin="member_profile",
        state=state,
        photo_metadata=photo_metadata,
        suggested_value=photo_sex,
        confidence=1.0,
    )


def _apply_canonical_height(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
    *,
    member_height_cm: Any,
) -> None:
    photo_height = _coerce_float(values.height_cm)
    photo_metadata = field_metadata.get("height_cm")
    profile_height = _coerce_float(member_height_cm)
    if not _is_plausible("height_cm", profile_height):
        profile_height = None

    if profile_height is None:
        if (
            photo_height is not None
            and photo_metadata is not None
            and photo_metadata.origin == "ai_image"
            and photo_metadata.state == "accepted"
        ):
            values.height_cm = photo_height
            field_metadata["height_cm"] = _canonical_metadata_with_suggestion(
                origin="ai_image",
                state="accepted",
                photo_metadata=photo_metadata,
                suggested_value=photo_height,
                confidence=photo_metadata.confidence,
            )
            return
        values.height_cm = None
        field_metadata["height_cm"] = _canonical_metadata_with_suggestion(
            origin="manual",
            state="conflict",
            photo_metadata=photo_metadata,
            suggested_value=photo_height,
        )
        _append_issue(
            issues,
            code="height_manual_confirmation_required",
            severity="critical",
            fields=["height_cm"],
            message="A altura do cadastro esta ausente ou invalida e precisa ser confirmada.",
        )
        return

    values.height_cm = profile_height
    state = "accepted"
    if photo_height is not None and abs(photo_height - profile_height) > 2:
        state = "conflict"
        _append_issue(
            issues,
            code="height_profile_conflict",
            severity="critical",
            fields=["height_cm"],
            message="A altura lida na foto diverge mais de 2 cm da altura cadastrada.",
        )
    field_metadata["height_cm"] = _canonical_metadata_with_suggestion(
        origin="member_profile",
        state=state,
        photo_metadata=photo_metadata,
        suggested_value=photo_height,
        confidence=1.0,
    )


def _validate_bmi_consistency(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
) -> None:
    weight = _coerce_float(values.weight_kg)
    height = _coerce_float(values.height_cm)
    printed_bmi = _coerce_float(values.bmi)
    if weight is None or height is None or printed_bmi is None or height <= 0:
        return
    calculated_bmi = weight / ((height / 100) ** 2)
    tolerance = max(0.5, abs(printed_bmi) * 0.02)
    if abs(printed_bmi - calculated_bmi) <= tolerance:
        return
    for field_name in ("weight_kg", "height_cm", "bmi"):
        metadata = field_metadata.get(field_name)
        if metadata:
            field_metadata[field_name] = metadata.model_copy(update={"state": "conflict"})
    _append_issue(
        issues,
        code="bmi_consistency_conflict",
        severity="critical",
        fields=["weight_kg", "height_cm", "bmi"],
        message="Peso, altura e IMC nao conferem entre si e precisam ser revisados.",
    )


def _validate_previous_weight(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
    *,
    previous_weight_kg: Any,
) -> None:
    weight = _coerce_float(values.weight_kg)
    previous_weight = _coerce_float(previous_weight_kg)
    if weight is None or previous_weight is None or previous_weight <= 0:
        return
    if abs(weight - previous_weight) / previous_weight <= 0.2:
        return
    _append_issue(
        issues,
        code="weight_previous_variation",
        severity="warning",
        fields=["weight_kg"],
        message="O peso variou mais de 20% em relacao a avaliacao anterior; confira antes de salvar.",
    )


def _canonical_metadata_with_suggestion(
    *,
    origin: str,
    state: str,
    photo_metadata: BodyCompositionFieldMetadata | None,
    suggested_value: Any,
    confidence: float | None = None,
) -> BodyCompositionFieldMetadata:
    return BodyCompositionFieldMetadata(
        origin=origin,
        state=state,
        confidence=confidence,
        label=photo_metadata.label if photo_metadata else None,
        evidence=photo_metadata.evidence if photo_metadata else None,
        suggested_value=suggested_value,
    )


def _age_on_date(birthdate: date | None, evaluation_date: date) -> int | None:
    if not isinstance(birthdate, date) or birthdate > evaluation_date:
        return None
    years = evaluation_date.year - birthdate.year
    if (evaluation_date.month, evaluation_date.day) < (birthdate.month, birthdate.day):
        years -= 1
    return years if 1 <= years <= 119 else None


def _is_physical_age_label(label: str, evidence: str) -> bool:
    text = f"{label} {evidence}".lower()
    return "physical age" in text or "idade fis" in text


def _append_issue(
    issues: list[BodyCompositionValidationIssue],
    *,
    code: str,
    severity: str,
    fields: list[str],
    message: str,
) -> None:
    issues.append(
        BodyCompositionValidationIssue(
            code=code,
            severity=severity,
            fields=fields,
            message=message,
        )
    )


def _issues_as_legacy_warnings(
    issues: list[BodyCompositionValidationIssue],
) -> list[BodyCompositionOcrWarning]:
    return [
        BodyCompositionOcrWarning(
            field=issue.fields[0] if len(issue.fields) == 1 else None,
            message=issue.message,
            severity=issue.severity,
        )
        for issue in issues
    ]


def _dedupe_issues(issues: list[BodyCompositionValidationIssue]) -> list[BodyCompositionValidationIssue]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    deduped: list[BodyCompositionValidationIssue] = []
    for issue in issues:
        key = (issue.code, tuple(issue.fields))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def _validated_confidence(
    field_metadata: dict[str, BodyCompositionFieldMetadata],
    issues: list[BodyCompositionValidationIssue],
) -> float:
    evidence_scores = [
        metadata.confidence
        for metadata in field_metadata.values()
        if metadata.origin == "ai_image" and metadata.confidence is not None and metadata.state != "unavailable"
    ]
    baseline = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.5
    critical_count = sum(issue.severity == "critical" for issue in issues)
    warning_count = len(issues) - critical_count
    return max(0.2, round(min(0.99, baseline - critical_count * 0.08 - warning_count * 0.02), 2))


def _complete_parse_request(
    result: BodyCompositionImageParseResultRead,
    *,
    started_at: float,
    provider: str | None,
    image_width: int | None,
    image_height: int | None,
    preprocessing: DocumentPreprocessingResult | None = None,
    capture_metadata: BodyCompositionCaptureMetadata | None = None,
    enhancement_retry_used: bool = False,
    enhancement_variant: str | None = None,
) -> BodyCompositionImageParseResultRead:
    duration_ms = max(0, round((perf_counter() - started_at) * 1000))
    local_result = result.engine == "local"
    processing = BodyCompositionImageProcessing(
        primary_engine="local_ocr" if local_result else "ai_image",
        fallback_used=local_result,
        duration_ms=duration_ms,
        provider=provider,
        image_width=image_width,
        image_height=image_height,
        capture_device_kind=capture_metadata.device_kind if capture_metadata else "unknown",
        capture_mode=capture_metadata.capture_mode if capture_metadata else "single",
        segment_count=(
            max(1, len(capture_metadata.segments))
            if capture_metadata and capture_metadata.capture_mode == "segmented"
            else 1
        ),
        enhancement_retry_used=enhancement_retry_used,
        enhancement_variant=enhancement_variant,
    )
    quality_codes = list(preprocessing.quality_codes if preprocessing else [])
    if capture_metadata:
        quality_codes.extend(code for code in capture_metadata.quality_codes if code not in quality_codes)
    preprocessing_payload = BodyCompositionImagePreprocessing(
        applied=bool(preprocessing and preprocessing.applied),
        method=preprocessing.method if preprocessing else "original",
        confidence=preprocessing.confidence if preprocessing else 0,
        source_width=preprocessing.source_width if preprocessing else image_width,
        source_height=preprocessing.source_height if preprocessing else image_height,
        output_width=preprocessing.output_width if preprocessing else image_width,
        output_height=preprocessing.output_height if preprocessing else image_height,
    )
    quality = BodyCompositionImageQuality(
        usable=not {"document_blurred", "document_dark"}.issubset(quality_codes),
        document_found=bool(preprocessing and preprocessing.confidence >= 0.45),
        codes=quality_codes,
        metrics=preprocessing.quality_metrics if preprocessing else {},
    )
    profile_conflicts: list[BodyCompositionProfileConflict] = []
    for field_name, issue_code in (
        ("age_years", "age_profile_conflict"),
        ("sex", "sex_profile_conflict"),
        ("height_cm", "height_profile_conflict"),
    ):
        if not any(issue.code == issue_code for issue in result.validation_issues):
            continue
        metadata = result.field_metadata.get(field_name)
        profile_conflicts.append(
            BodyCompositionProfileConflict(
                field=field_name,
                profile_value=getattr(result.values, field_name, None),
                image_value=metadata.suggested_value if metadata else None,
            )
        )
    suggested_resolution = None
    capture_recommendation = None
    raw_short_side = preprocessing.quality_metrics.get("receipt_short_side_raw", 0) if preprocessing else 0
    if raw_short_side and raw_short_side < 480:
        suggested_resolution = "Aproxime a folha para o texto ocupar mais da imagem."
        if raw_short_side < 320:
            capture_recommendation = {
                "mode": "segmented",
                "reason": "insufficient_text_density",
                "required_segments": ["top", "middle", "bottom"],
                "message": "Aproxime o papel ou fotografe em partes.",
            }
    completed = result.model_copy(update={
        "processing": processing,
        "image_quality": quality,
        "preprocessing": preprocessing_payload,
        "profile_conflicts": profile_conflicts,
        "suggested_resolution": suggested_resolution,
        "capture_recommendation": capture_recommendation,
    })
    populated_fields = sorted(
        field_name
        for field_name in BodyCompositionOcrValues.model_fields
        if getattr(completed.values, field_name, None) is not None
    )
    issue_codes = sorted({issue.code for issue in completed.validation_issues})
    logger.info(
        "body_composition_image_parse_complete provider=%s engine=%s fallback=%s duration_ms=%s "
        "image_width=%s image_height=%s enhancement_retry=%s fields=%s issue_codes=%s",
        provider or "unavailable",
        processing.primary_engine,
        processing.fallback_used,
        duration_ms,
        image_width,
        image_height,
        processing.enhancement_retry_used,
        ",".join(populated_fields),
        ",".join(issue_codes),
    )
    return completed


def _classify_assisted_read_failure(exc: Exception) -> tuple[str, str]:
    error_text = str(exc).lower()
    error_code = str(getattr(exc, "code", "") or "").lower()
    status_code = getattr(exc, "status_code", None)

    if error_code == "insufficient_quota" or "insufficient_quota" in error_text or "current quota" in error_text:
        return (
            "Leitura assistida indisponivel: a cota do provedor de IA foi esgotada. "
            "Regularize os creditos da integracao ou tente novamente depois.",
            "critical",
        )
    if status_code == 429 or "rate limit" in error_text or "too many requests" in error_text:
        return (
            "Leitura assistida temporariamente limitada pelo provedor de IA. Tente novamente em alguns minutos.",
            "warning",
        )
    if "timeout" in error_text or "timed out" in error_text:
        return (
            "Leitura assistida excedeu o tempo limite. Tente novamente com uma imagem menor e mais nitida.",
            "warning",
        )
    return (
        "Leitura assistida por IA falhou no momento; mantivemos o OCR local para revisao manual.",
        "warning",
    )


def _compute_confidence(
    *,
    engine: str,
    warnings: list[BodyCompositionOcrWarning],
    ai_used_count: int,
    local_used_count: int,
    local_confidence: float,
    preserve_baseline: bool = False,
) -> float:
    critical_count = sum(1 for item in warnings if item.severity == "critical")
    warning_count = len(warnings) - critical_count
    if preserve_baseline:
        base = local_confidence
    elif engine == "ai_assisted":
        base = local_confidence
    elif engine == "ai_fallback":
        base = local_confidence
    elif engine == "hybrid":
        base = min(0.95, local_confidence)
        if local_used_count > ai_used_count:
            base -= 0.05
    else:
        base = min(local_confidence, 0.72)

    confidence = base - critical_count * 0.08 - warning_count * 0.025
    return max(0.2, round(min(0.99, confidence), 2))


def _choose_value_source(
    field_name: str,
    ai_value: Any,
    local_value: Any,
    _local_warnings: list[BodyCompositionOcrWarning] | None = None,
) -> str | None:
    ai_plausible = _is_plausible(field_name, ai_value)
    local_plausible = _is_plausible(field_name, local_value)

    if ai_plausible and local_plausible:
        return "ai"
    if ai_plausible:
        return "ai"
    if local_plausible:
        return "local"
    if ai_value is not None:
        return "ai"
    if local_value is not None:
        return "local"
    return None


def _choose_range(
    ai_range: BodyCompositionRangeValue | None,
    local_range: BodyCompositionRangeValue | None,
) -> BodyCompositionRangeValue | None:
    if _range_has_values(ai_range):
        return ai_range
    if _range_has_values(local_range):
        return local_range
    return None


def _warnings_for_field(
    warnings: list[BodyCompositionOcrWarning],
    field_name: str | None,
) -> list[BodyCompositionOcrWarning]:
    return [warning for warning in warnings if warning.field == field_name]


def _warnings_for_field_without_local_ai_fallback(
    warnings: list[BodyCompositionOcrWarning],
    field_name: str | None,
) -> list[BodyCompositionOcrWarning]:
    return [
        warning
        for warning in warnings
        if warning.field == field_name and not _is_local_ai_unavailable_warning(warning)
    ]


def _is_local_ai_unavailable_warning(warning: BodyCompositionOcrWarning) -> bool:
    message = (warning.message or "").lower()
    return "leitura assistida por ia indisponivel" in message or "leitura assistida por ia falhou" in message


def _range_has_values(value: BodyCompositionRangeValue | None) -> bool:
    return bool(value and (value.min is not None or value.max is not None))


def _build_local_hint(local_ocr_result: BodyCompositionImageOcrPayload | None) -> dict[str, Any]:
    if local_ocr_result is None:
        return {"available": False}
    return {
        "available": True,
        "values": local_ocr_result.values.model_dump(exclude_none=True),
        "warnings": [warning.model_dump() for warning in local_ocr_result.warnings[:8]],
        "confidence": local_ocr_result.confidence,
        "raw_text_excerpt": local_ocr_result.raw_text[:4000],
    }


def _normalize_device_profile(value: str) -> BodyCompositionDeviceProfile:
    normalized = (value or "").strip()
    if normalized != "tezewa_receipt_v1":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="device_profile nao suportado")
    return "tezewa_receipt_v1"


def _validate_image_payload(image_bytes: bytes, media_type: str | None) -> str:
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo de imagem vazio")
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem excede o limite de 8 MB",
        )

    normalized = SUPPORTED_MEDIA_TYPES.get((media_type or "").lower())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de arquivo nao suportado. Use JPEG, PNG ou WEBP.",
        )
    return normalized


def _image_ai_available(provider: str | None = None) -> bool:
    resolved_provider = provider or _resolve_image_ai_provider()
    if not settings.body_composition_image_ai_enabled or not resolved_provider:
        return False
    if resolved_provider == "claude":
        return not claude_circuit_breaker.is_open()
    return True


def _normalize_values(source: Any) -> dict[str, Any]:
    payload = source if isinstance(source, dict) else {}
    normalized: dict[str, Any] = {}
    for field_name in BodyCompositionOcrValues.model_fields:
        raw_value = payload.get(field_name)
        if field_name == "evaluation_date":
            normalized[field_name] = _normalize_date_string(raw_value)
            continue
        if field_name == "sex":
            normalized[field_name] = _normalize_sex_value(raw_value)
            continue
        if field_name in TEXT_FIELDS:
            normalized[field_name] = _normalize_datetime_string(raw_value)
            continue
        if field_name in INT_FIELDS:
            normalized[field_name] = _coerce_int(raw_value)
            continue
        normalized[field_name] = _coerce_float(raw_value)
    return normalized


def _read_image_dimensions(image_bytes: bytes, media_type: str) -> tuple[int | None, int | None]:
    """Read common image dimensions without decoding or retaining the image."""
    try:
        if media_type == "image/png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n") and len(image_bytes) >= 24:
            return struct.unpack(">II", image_bytes[16:24])
        if media_type == "image/jpeg" and image_bytes.startswith(b"\xff\xd8"):
            offset = 2
            while offset + 9 <= len(image_bytes):
                if image_bytes[offset] != 0xFF:
                    offset += 1
                    continue
                marker = image_bytes[offset + 1]
                offset += 2
                if marker in {0xD8, 0xD9}:
                    continue
                if offset + 2 > len(image_bytes):
                    break
                segment_length = int.from_bytes(image_bytes[offset : offset + 2], "big")
                if segment_length < 2 or offset + segment_length > len(image_bytes):
                    break
                if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                    height = int.from_bytes(image_bytes[offset + 3 : offset + 5], "big")
                    width = int.from_bytes(image_bytes[offset + 5 : offset + 7], "big")
                    return width or None, height or None
                offset += segment_length
    except (IndexError, struct.error, ValueError):
        return None, None
    return None, None


def _normalize_field_metadata(source: Any) -> dict[str, BodyCompositionFieldMetadata]:
    payload = source if isinstance(source, dict) else {}
    normalized: dict[str, BodyCompositionFieldMetadata] = {}
    for field_name, raw_metadata in payload.items():
        if field_name not in BodyCompositionOcrValues.model_fields or not isinstance(raw_metadata, dict):
            continue
        label = _truncate_evidence(raw_metadata.get("label"))
        evidence = _truncate_evidence(raw_metadata.get("evidence"))
        confidence = _coerce_float(raw_metadata.get("confidence"))
        if confidence is not None:
            confidence = max(0.0, min(1.0, confidence))
        normalized[field_name] = BodyCompositionFieldMetadata(
            origin="ai_image",
            state="accepted" if confidence is not None and confidence >= MIN_EVIDENCE_CONFIDENCE else "suggested",
            confidence=confidence,
            label=label,
            evidence=evidence,
            suggested_value=_normalize_metadata_value(field_name, raw_metadata.get("suggested_value")),
        )
    return normalized


def _normalize_metadata_value(field_name: str, value: Any) -> str | int | float | None:
    if field_name == "evaluation_date":
        return _normalize_date_string(value)
    if field_name == "measured_at":
        return _normalize_datetime_string(value)
    if field_name == "sex":
        return _normalize_sex_value(value)
    if field_name in INT_FIELDS:
        return _coerce_int(value)
    return _coerce_float(value)


def _initial_ai_confidence(
    values: BodyCompositionOcrValues,
    field_metadata: dict[str, BodyCompositionFieldMetadata],
) -> float:
    scores = [
        metadata.confidence
        for field_name, metadata in field_metadata.items()
        if getattr(values, field_name, None) is not None
        and metadata.confidence is not None
        and metadata.label
        and metadata.evidence
    ]
    if not scores:
        return 0.5
    return max(0.2, round(min(0.99, sum(scores) / len(scores)), 2))


def _normalize_ranges(source: Any) -> dict[str, BodyCompositionRangeValue]:
    payload = source if isinstance(source, dict) else {}
    normalized: dict[str, BodyCompositionRangeValue] = {}
    for field_name, range_value in payload.items():
        if not isinstance(range_value, dict):
            continue
        normalized[field_name] = BodyCompositionRangeValue(
            min=_coerce_float(range_value.get("min")),
            max=_coerce_float(range_value.get("max")),
        )
    return normalized


def _normalize_warnings(source: Any) -> list[BodyCompositionOcrWarning]:
    if not isinstance(source, list):
        return []

    normalized: list[BodyCompositionOcrWarning] = []
    for item in source:
        if isinstance(item, str):
            normalized.append(BodyCompositionOcrWarning(field=None, message=item, severity="warning"))
            continue
        if not isinstance(item, dict):
            continue
        normalized.append(
            BodyCompositionOcrWarning(
                field=_normalize_string(item.get("field")),
                message=str(item.get("message") or "").strip() or "Leitura assistida retornou aviso sem detalhe.",
                severity="critical" if str(item.get("severity") or "").strip().lower() == "critical" else "warning",
            )
        )
    return normalized


def _normalize_date_string(value: Any) -> str | None:
    text = _normalize_string(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_date(value: Any) -> date | None:
    normalized = _normalize_date_string(value)
    return date.fromisoformat(normalized) if normalized else None


def _normalize_datetime_string(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    text = _normalize_string(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def _normalize_sex_value(value: Any) -> str | None:
    normalized = (_normalize_string(value) or "").lower()
    aliases = {
        "male": "male",
        "man": "male",
        "men": "male",
        "masculino": "male",
        "homem": "male",
        "m": "male",
        "female": "female",
        "woman": "female",
        "women": "female",
        "feminino": "female",
        "mulher": "female",
        "f": "female",
    }
    return aliases.get(normalized)


def _truncate_evidence(value: Any, limit: int = 160) -> str | None:
    text = _normalize_string(value)
    if not text:
        return None
    return text[:limit]


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _coerce_int(value: Any) -> int | None:
    numeric = _coerce_float(value)
    if numeric is None:
        return None
    return round(numeric)


def _normalize_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _is_plausible(field_name: str, value: Any) -> bool:
    if value is None:
        return False
    if field_name == "evaluation_date":
        return _normalize_date_string(value) is not None
    if field_name == "measured_at":
        return _normalize_datetime_string(value) is not None
    if field_name == "sex":
        return _normalize_sex_value(value) is not None

    numeric = _coerce_float(value)
    if numeric is None:
        return False
    bounds = PLAUSIBLE_RANGES.get(field_name)
    if bounds is None:
        return True
    minimum, maximum = bounds
    return minimum <= numeric <= maximum


def _values_close(field_name: str, left: Any, right: Any) -> bool:
    if field_name == "evaluation_date":
        return _normalize_date_string(left) == _normalize_date_string(right)
    left_value = _coerce_float(left)
    right_value = _coerce_float(right)
    if left_value is None or right_value is None:
        return left_value == right_value
    tolerance = 0.2 if field_name not in INT_FIELDS else 1.0
    return abs(left_value - right_value) <= tolerance


def _dedupe_warnings(warnings: list[BodyCompositionOcrWarning]) -> list[BodyCompositionOcrWarning]:
    seen: set[tuple[str | None, str, str]] = set()
    deduped: list[BodyCompositionOcrWarning] = []
    for warning in warnings:
        key = (warning.field, warning.message, warning.severity)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped
