from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Any

import anthropic
from fastapi import HTTPException, status
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.circuit_breaker import claude_circuit_breaker
from app.core.config import settings
from app.schemas.body_composition import (
    BodyCompositionDeviceProfile,
    BodyCompositionImageOcrPayload,
    BodyCompositionImageParseResultRead,
    BodyCompositionOcrValues,
    BodyCompositionOcrWarning,
    BodyCompositionRangeValue,
)
from app.services.body_composition_report_service import build_body_composition_quality_flags
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
INT_FIELDS = {"physical_age", "health_score"}
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
    ("fat_free_mass_kg", "Fat-free mass (kg)"),
    ("inorganic_salt_kg", "Inorganic salt (kg)"),
    ("muscle_mass_kg", "Muscle mass (kg)"),
    ("protein_kg", "Protein (kg)"),
    ("body_water_kg", "Body water (kg)"),
    ("lean_mass_kg", "Lean mass (kg), quando existir nessa versao do recibo"),
    ("body_water_percent", "Body water ratio (%)"),
    ("visceral_fat_level", "Visceral fat"),
    ("bmi", "BMI"),
    ("basal_metabolic_rate_kcal", "BMR ou basal metabolic rate (kcal)"),
    ("skeletal_muscle_kg", "Skeletal muscle (kg)"),
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


def _build_values_template() -> str:
    template = {field_name: None for field_name in BodyCompositionOcrValues.model_fields}
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
        "Retorne APENAS JSON com chaves: device_model, values, ranges, warnings, needs_review.\n"
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
        "- percorra todo o recibo; nao pare nos campos principais e cubra composicao corporal, metabolismo, comprehensive evaluation e controles\n"
        "- values deve conter TODAS as chaves esperadas do sistema, mesmo quando o valor for null\n"
        "- diferencie obrigatoriamente body_fat_kg de body_fat_percent\n"
        "- body_fat_kg corresponde a 'Body fat (kg)'\n"
        "- body_fat_percent corresponde a 'Body fat ratio (%)'\n"
        "- body_water_kg e body_water_percent sao campos diferentes e podem coexistir\n"
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
        f"- dica opcional do OCR local: {json.dumps(local_hint, ensure_ascii=False)}\n"
        "Responda em portugues do Brasil."
    )


def parse_body_composition_image(
    *,
    image_bytes: bytes,
    media_type: str | None,
    device_profile: str,
    local_ocr_result: BodyCompositionImageOcrPayload | None = None,
) -> BodyCompositionImageParseResultRead:
    normalized_device_profile = _normalize_device_profile(device_profile)
    normalized_media_type = _validate_image_payload(image_bytes, media_type)
    provider = _resolve_image_ai_provider()

    local_payload = BodyCompositionImageOcrPayload.model_validate(local_ocr_result.model_dump()) if local_ocr_result else None

    if not _image_ai_available(provider):
        return _build_local_only_result(
            local_payload,
            "Leitura assistida por IA indisponivel; mantivemos a leitura local com revisao manual obrigatoria.",
            normalized_device_profile,
        )

    try:
        if provider == "openai":
            ai_payload = _parse_with_openai_vision(
                image_bytes=image_bytes,
                media_type=normalized_media_type,
                device_profile=normalized_device_profile,
                local_ocr_result=local_payload,
            )
        else:
            ai_payload = _parse_with_claude_vision(
                image_bytes=image_bytes,
                media_type=normalized_media_type,
                device_profile=normalized_device_profile,
                local_ocr_result=local_payload,
            )
        if provider == "claude":
            claude_circuit_breaker.record_success()
    except Exception:
        if provider == "claude":
            claude_circuit_breaker.record_failure()
        logger.exception(
            "Falha na leitura assistida de bioimpedancia com provedor %s. Mantendo OCR local quando possivel.",
            provider or "indisponivel",
        )
        return _build_local_only_result(
            local_payload,
            "Leitura assistida por IA falhou no momento; mantivemos o OCR local para revisao manual.",
            normalized_device_profile,
        )

    return _merge_parse_results(local_payload, ai_payload)


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
    )


def _parse_with_openai_vision(
    *,
    image_bytes: bytes,
    media_type: str,
    device_profile: BodyCompositionDeviceProfile,
    local_ocr_result: BodyCompositionImageOcrPayload | None,
) -> BodyCompositionImageParseResultRead:
    prompt = _build_vision_prompt(
        device_profile=device_profile,
        local_ocr_result=local_ocr_result,
        provider_name="openai",
    )

    client = _create_openai_client(timeout_seconds=settings.body_composition_image_ai_timeout_seconds)
    response = client.chat.completions.create(
        model=settings.openai_vision_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Extraia os dados estruturados de bioimpedancia com alta precisao e sem inventar valores. Responda somente JSON valido.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64.b64encode(image_bytes).decode('ascii')}",
                        },
                    },
                ],
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
    image_bytes: bytes,
    media_type: str,
    device_profile: BodyCompositionDeviceProfile,
    local_ocr_result: BodyCompositionImageOcrPayload | None,
) -> BodyCompositionImageParseResultRead:
    prompt = _build_vision_prompt(
        device_profile=device_profile,
        local_ocr_result=local_ocr_result,
        provider_name="claude",
    )
    prompt = (
        f"{prompt}\n"
        "JSON esperado:\n"
        "{"
        "\"device_model\": \"Tezewa ou null\", "
        "\"values\": "
        f"{_build_values_template()}, "
        "\"ranges\": {\"weight_kg\": {\"min\": 61.7, \"max\": 75.5}}, "
        "\"warnings\": [], "
        "\"needs_review\": false"
        "}\n"
    )

    client = anthropic.Anthropic(
        api_key=settings.claude_api_key,
        timeout=settings.body_composition_image_ai_timeout_seconds,
    )
    response = client.messages.create(
        model=settings.claude_vision_model or settings.claude_model,
        max_tokens=max(settings.claude_max_tokens, 900),
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        },
                    },
                ],
            }
        ],
    )
    response_text = "\n".join(
        block.text for block in response.content if getattr(block, "type", None) == "text" and getattr(block, "text", None)
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

    values = BodyCompositionOcrValues.model_validate(_normalize_values(values_source))
    ranges = _normalize_ranges(ranges_source)
    warnings = _normalize_warnings(warnings_source)

    return BodyCompositionImageParseResultRead(
        device_profile=device_profile,
        device_model=_normalize_string(payload.get("device_model")) or (local_ocr_result.device_model if local_ocr_result else None),
        values=values,
        ranges=ranges,
        warnings=warnings,
        confidence=0.94,
        raw_text=local_ocr_result.raw_text if local_ocr_result else "",
        needs_review=bool(payload.get("needs_review", False)),
        engine="ai_assisted",
        fallback_used=False,
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
            warnings.extend(_warnings_for_field(ai_result.warnings, field_name))
            if local_value is not None and ai_value is not None and not _values_close(field_name, ai_value, local_value):
                warnings.append(
                    BodyCompositionOcrWarning(
                        field=field_name,
                        message=f"{field_name} do OCR local foi substituido pela leitura assistida da imagem.",
                        severity="warning",
                    )
                )
        elif source == "local":
            local_used_fields.add(field_name)
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
        local_confidence=local_result.confidence,
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
        )
    )


def _build_local_only_result(
    local_result: BodyCompositionImageOcrPayload | None,
    message: str,
    device_profile: BodyCompositionDeviceProfile,
) -> BodyCompositionImageParseResultRead:
    if local_result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Leitura assistida indisponivel e nenhum OCR local foi fornecido.",
        )

    warnings = list(local_result.warnings)
    warnings.append(BodyCompositionOcrWarning(field=None, message=message, severity="warning"))
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
        )
    )


def _finalize_parse_result(result: BodyCompositionImageParseResultRead) -> BodyCompositionImageParseResultRead:
    deduped_warnings = _dedupe_warnings(result.warnings)
    needs_review = any(item.severity == "critical" for item in deduped_warnings) or result.needs_review or result.confidence < 0.85
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
        values=result.values,
        ranges=result.ranges,
        warnings=deduped_warnings,
        flags=build_body_composition_quality_flags(
            result.values,
            parsing_confidence=confidence,
            needs_review=needs_review,
        ),
        confidence=confidence,
        raw_text=result.raw_text,
        needs_review=needs_review,
        engine=result.engine,
        fallback_used=result.fallback_used,
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
        base = 0.94 if ai_used_count >= 4 else 0.88
    elif engine == "ai_fallback":
        base = 0.94 if ai_used_count >= 4 else 0.88
    elif engine == "hybrid":
        base = 0.9 if ai_used_count >= 3 else 0.84
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
    local_warnings: list[BodyCompositionOcrWarning] | None = None,
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


def _warnings_for_field(warnings: list[BodyCompositionOcrWarning], field_name: str | None) -> list[BodyCompositionOcrWarning]:
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
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Imagem excede o limite de 8 MB")

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
        if field_name in INT_FIELDS:
            normalized[field_name] = _coerce_int(raw_value)
            continue
        normalized[field_name] = _coerce_float(raw_value)
    return normalized


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


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
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
    return int(round(numeric))


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
