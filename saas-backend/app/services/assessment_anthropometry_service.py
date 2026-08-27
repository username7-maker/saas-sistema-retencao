from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_dashboard_cache
from app.models import Member, Task, TaskPriority, TaskStatus
from app.models.assessment import Assessment
from app.services.body_composition_anthropometry_service import (
    ANTHROPOMETRY_CALCULATION_FIELDS,
    ANTHROPOMETRY_EVOLUTION_FIELDS,
)
from app.services.body_composition_actuar_sync_service import prepare_anthropometric_assessment_sync_attempt
from app.services.body_composition_protocols import calculate_protocol_body_fat, get_protocol, protocol_catalog
from app.utils.localized_numbers import LocalizedNumberError, parse_localized_decimal


ASSESSMENT_METHOD = "manual_anthropometry"
RECORD_ORIGIN = "cordex"
MEASUREMENT_POLICY_VERSION = "anthropometry-v2"
INDICATOR_MANUAL_MEASURED = "manual_measured"
INDICATOR_ANTHROPOMETRY_CALCULATED = "anthropometry_calculated"
INDICATOR_UNAVAILABLE = "unavailable"

_Q1 = Decimal("0.1")
_Q2 = Decimal("0.01")
_D100 = Decimal("100")
_WARNING_ONLY_PROTOCOL_FLAGS = {"anthropometry_protocol_age_outside_range"}
LEE_FORMULA_VERSION = "lee-2000-complete-v1"
LEE_REQUIRED_FIELDS = {
    "right_arm_relaxed_cm",
    "right_thigh_cm",
    "right_calf_cm",
    "skinfold_triceps_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
}

_FIELD_LABELS = {
    "height_cm": "Altura",
    "weight_kg": "Peso",
    "neck_cm": "Pescoco",
    "waist_cm": "Cintura",
    "hip_cm": "Quadril",
    "abdomen_cm": "Abdomen",
    "shoulders_cm": "Ombros",
    "chest_cm": "Torax",
    "arm_cm": "Braco",
    "right_arm_relaxed_cm": "Braco direito relaxado",
    "left_arm_relaxed_cm": "Braco esquerdo relaxado",
    "right_arm_flexed_cm": "Braco direito contraido",
    "left_arm_flexed_cm": "Braco esquerdo contraido",
    "thigh_cm": "Coxa",
    "right_thigh_cm": "Coxa direita",
    "left_thigh_cm": "Coxa esquerda",
    "right_calf_cm": "Panturrilha direita",
    "left_calf_cm": "Panturrilha esquerda",
    "skinfold_chest_mm": "Dobra peitoral",
    "skinfold_midaxillary_mm": "Dobra axilar media",
    "skinfold_subscapular_mm": "Dobra subescapular",
    "skinfold_triceps_mm": "Dobra tricipital",
    "skinfold_biceps_mm": "Dobra bicipital",
    "skinfold_abdominal_mm": "Dobra abdominal",
    "skinfold_suprailiac_mm": "Dobra suprailiaca",
    "skinfold_thigh_mm": "Dobra coxa",
    "skinfold_calf_mm": "Dobra panturrilha",
}

_UNAVAILABLE_METRICS = {
    "muscle_mass_kg": "Massa muscular: indisponivel nesta modalidade",
    "body_water_percent": "Agua corporal: indisponivel nesta modalidade",
    "visceral_fat_level": "Gordura visceral: indisponivel nesta modalidade",
    "bone_mass_kg": "Massa ossea: indisponivel nesta modalidade",
    "metabolic_age": "Idade metabolica/fisica: indisponivel nesta modalidade",
    "total_energy_expenditure": "Gasto energetico total sem fator de atividade: indisponivel nesta modalidade",
    "target_weight_kg": "Peso-alvo sem meta definida: indisponivel nesta modalidade",
}

_PERIMETRY_EVOLUTION_FIELDS = tuple(
    dict.fromkeys((*ANTHROPOMETRY_CALCULATION_FIELDS, *ANTHROPOMETRY_EVOLUTION_FIELDS))
)


def list_supported_anthropometry_protocols() -> list[dict[str, Any]]:
    return [item for item in protocol_catalog() if item.get("supported") is True]


def preview_anthropometric_assessment(payload: Any, *, member: Member | None = None) -> dict[str, Any]:
    data = _as_dict(payload)
    assessment_date = _normalize_datetime(data.get("assessment_date"))
    protocol_key = str(data.get("measurement_protocol") or "").strip()
    protocol = get_protocol(protocol_key)
    if protocol is None:
        _raise_unprocessable("anthropometry_protocol_unknown", {"protocol": protocol_key})
    if not protocol.supported or protocol.calculation is None:
        _raise_unprocessable("anthropometry_protocol_manual_only", {"protocol": protocol_key})

    sex = _resolve_sex(data, member)
    age_years = _resolve_age(data, member, assessment_date)
    ethnicity = data.get("anthropometry_ethnicity")
    maturity = data.get("anthropometry_maturity")
    calculate_muscle_mass = bool(data.get("calculate_muscle_mass"))
    allowed_choices = {
        "anthropometry_ethnicity": {"white", "black"},
        "anthropometry_maturity": {"prepubertal", "pubertal", "postpubertal"},
    }
    for field in protocol.required_choice_fields:
        if data.get(field) not in allowed_choices.get(field, set()):
            _raise_unprocessable("anthropometry_choice_invalid", {"field": field})
    if calculate_muscle_mass and ethnicity not in {"white", "black", "asian"}:
        _raise_unprocessable("anthropometry_choice_invalid", {"field": "anthropometry_ethnicity"})
    raw_measurements = _as_dict(data.get("measurements") or {})
    required_fields = {"height_cm", "weight_kg", *protocol.required_fields}
    if calculate_muscle_mass:
        required_fields.update(LEE_REQUIRED_FIELDS)
    consolidated_measurements = _consolidate_measurements(raw_measurements, required_fields=required_fields)

    if "height_cm" not in consolidated_measurements and member is not None and getattr(member, "height_cm", None) is not None:
        consolidated_measurements["height_cm"] = _profile_measurement("height_cm", getattr(member, "height_cm"))
    if "weight_kg" not in consolidated_measurements:
        _raise_unprocessable("anthropometry_missing_required_measurement", {"field": "weight_kg"})
    if "height_cm" not in consolidated_measurements:
        _raise_unprocessable("anthropometry_missing_required_measurement", {"field": "height_cm"})
    if calculate_muscle_mass:
        for field in sorted(LEE_REQUIRED_FIELDS):
            if field not in consolidated_measurements:
                _raise_unprocessable("anthropometry_missing_required_measurement", {"field": field})

    formula_values = {
        "measurement_protocol": protocol.key,
        "sex": sex,
        "age_years": age_years,
        "anthropometry_ethnicity": ethnicity,
        "anthropometry_maturity": maturity,
        **{field: float(item["decimal_value"]) for field, item in consolidated_measurements.items()},
    }
    protocol_result = calculate_protocol_body_fat(formula_values)
    blocking_protocol_flags = _blocking_protocol_flags(protocol_result.get("flags", []))
    if blocking_protocol_flags or protocol_result.get("body_fat_percent") is None:
        _raise_unprocessable(
            "anthropometry_protocol_not_calculable",
            {
                "protocol": protocol.key,
                "flags": blocking_protocol_flags,
                "missing_fields": protocol_result.get("missing_fields", []),
            },
        )

    weight = consolidated_measurements["weight_kg"]["decimal_value"]
    height = consolidated_measurements["height_cm"]["decimal_value"]
    body_fat_pct = _round2(protocol_result["body_fat_percent"])
    if body_fat_pct < Decimal("0") or body_fat_pct > Decimal("75"):
        _raise_unprocessable("implausible_measurement", {"field": "body_fat_pct", "value": str(body_fat_pct)})
    fat_mass = _round2(weight * body_fat_pct / _D100)
    lean_mass = _round2(weight - fat_mass)
    bmi = _calculate_bmi(height, weight)
    waist_hip_ratio = _calculate_waist_hip_ratio(consolidated_measurements)
    basal_metabolic_rate = _calculate_mifflin_bmr(sex=sex, age_years=age_years, height_cm=height, weight_kg=weight)
    muscle_mass = (
        _calculate_lee_muscle_mass(
            sex=sex,
            age_years=age_years,
            height_cm=height,
            ethnicity=str(ethnicity),
            measurements=consolidated_measurements,
        )
        if calculate_muscle_mass
        else None
    )
    muscle_flags: list[str] = []
    if calculate_muscle_mass and age_years < 18:
        muscle_flags.append("lee_age_extrapolation")
    if calculate_muscle_mass and bmi >= Decimal("30"):
        muscle_flags.append("lee_bmi_extrapolation")
    formula_version = f"{MEASUREMENT_POLICY_VERSION}:{protocol.key}"
    if calculate_muscle_mass:
        formula_version = f"{formula_version}:{LEE_FORMULA_VERSION}"

    unavailable_metrics = dict(_UNAVAILABLE_METRICS)
    if muscle_mass is not None:
        unavailable_metrics.pop("muscle_mass_kg", None)

    results = {
        "bmi": bmi,
        "body_fat_pct": body_fat_pct,
        "fat_mass_kg": fat_mass,
        "lean_mass_kg": lean_mass,
        "waist_hip_ratio": waist_hip_ratio,
        "basal_metabolic_rate": basal_metabolic_rate,
        "muscle_mass_kg": muscle_mass,
        "body_water_percent": None,
        "visceral_fat_level": None,
        "bone_mass_kg": None,
        "metabolic_age": None,
        "total_energy_expenditure": None,
        "target_weight_kg": None,
    }
    indicator_origins = {
        "height_cm": INDICATOR_MANUAL_MEASURED,
        "weight_kg": INDICATOR_MANUAL_MEASURED,
        "bmi": INDICATOR_ANTHROPOMETRY_CALCULATED,
        "body_fat_pct": INDICATOR_ANTHROPOMETRY_CALCULATED,
        "fat_mass_kg": INDICATOR_ANTHROPOMETRY_CALCULATED,
        "lean_mass_kg": INDICATOR_ANTHROPOMETRY_CALCULATED,
        "waist_hip_ratio": INDICATOR_ANTHROPOMETRY_CALCULATED if waist_hip_ratio is not None else INDICATOR_UNAVAILABLE,
        "basal_metabolic_rate": INDICATOR_ANTHROPOMETRY_CALCULATED if basal_metabolic_rate is not None else INDICATOR_UNAVAILABLE,
        **{key: INDICATOR_UNAVAILABLE for key in unavailable_metrics},
        "muscle_mass_kg": INDICATOR_ANTHROPOMETRY_CALCULATED if muscle_mass is not None else INDICATOR_UNAVAILABLE,
    }

    snapshot = {
        "schema_version": "anthropometry_snapshot_v2",
        "measurement_policy_version": MEASUREMENT_POLICY_VERSION,
        "assessment_method": ASSESSMENT_METHOD,
        "record_origin": RECORD_ORIGIN,
        "assessment_date": assessment_date.isoformat(),
        "protocol": {
            "key": protocol.key,
            "label": protocol.label,
            "sex": protocol.sex,
            "age_min": protocol.age_min,
            "age_max": protocol.age_max,
            "required_fields": list(protocol.required_fields),
            "required_choice_fields": list(protocol.required_choice_fields),
            "formula_version": formula_version,
        },
        "inputs": {
            "sex_used_for_formula": sex,
            "age_used_for_formula": age_years,
            "height_used_for_formula": _decimal_str(height),
            "weight_used_for_formula": _decimal_str(weight),
            "anthropometry_ethnicity": ethnicity,
            "anthropometry_maturity": maturity,
            "calculate_muscle_mass": calculate_muscle_mass,
        },
        "measurements": {
            key: _snapshot_measurement(value)
            for key, value in sorted(consolidated_measurements.items())
        },
        "results": _snapshot_results(results),
        "indicator_origins": indicator_origins,
        "muscle_mass_calculation": _lee_snapshot(
            enabled=calculate_muscle_mass,
            result=muscle_mass,
            ethnicity=str(ethnicity) if ethnicity else None,
            sex=sex,
            age_years=age_years,
            measurements=consolidated_measurements,
            flags=muscle_flags,
        ),
        "unavailable_metrics": unavailable_metrics,
        "flags": list(dict.fromkeys([*(protocol_result.get("flags") or []), *muscle_flags])),
        "rounding_policy": "calculation_decimal_unrounded_inputs_final_2_decimals",
    }
    calculation_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    snapshot["calculation_hash"] = calculation_hash

    return {
        "assessment_method": ASSESSMENT_METHOD,
        "record_origin": RECORD_ORIGIN,
        "measurement_policy_version": MEASUREMENT_POLICY_VERSION,
        "protocol": {
            "key": protocol.key,
            "label": protocol.label,
            "sex": protocol.sex,
            "age_min": protocol.age_min,
            "age_max": protocol.age_max,
            "required_fields": list(protocol.required_fields),
            "required_choice_fields": list(protocol.required_choice_fields),
            "supported": protocol.supported,
            "notes": protocol.notes,
        },
        "formula_version": formula_version,
        "calculation_hash": calculation_hash,
        "results": results,
        "indicator_origins": indicator_origins,
        "snapshot": snapshot,
    }


def create_anthropometric_assessment(
    db: Session,
    *,
    member_id: UUID,
    evaluator_id: UUID,
    gym_id: UUID,
    payload: Any,
    idempotency_key: UUID,
    commit: bool = True,
) -> Assessment:
    existing = db.scalar(
        select(Assessment).where(
            Assessment.gym_id == gym_id,
            Assessment.idempotency_key == idempotency_key,
            Assessment.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return existing

    member = db.scalar(
        select(Member)
        .where(Member.id == member_id, Member.gym_id == gym_id, Member.deleted_at.is_(None))
        .with_for_update()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro nao encontrado")

    preview = preview_anthropometric_assessment(payload, member=member)
    assessment_date = _normalize_datetime(_as_dict(payload).get("assessment_date"))
    next_due = (assessment_date + timedelta(days=90)).date()
    previous_number = db.scalar(
        select(func.max(Assessment.assessment_number)).where(
            Assessment.gym_id == gym_id,
            Assessment.member_id == member_id,
            Assessment.deleted_at.is_(None),
        )
    ) or 0
    results = preview["results"]
    snapshot = dict(preview["snapshot"])
    snapshot["responsible_user_id"] = str(evaluator_id)
    snapshot["confirmed_at"] = datetime.now(tz=timezone.utc).isoformat()
    snapshot["calculation_hash"] = preview["calculation_hash"]

    measurement_values = {
        key: Decimal(str(value["consolidated_value"]))
        for key, value in snapshot["measurements"].items()
        if value.get("consolidated_value") is not None
    }
    perimetry_evolution = _extract_perimetry_evolution_values(measurement_values)
    assessment = Assessment(
        id=uuid.uuid4(),
        gym_id=gym_id,
        member_id=member_id,
        evaluator_id=evaluator_id,
        assessment_number=int(previous_number) + 1,
        assessment_date=assessment_date,
        next_assessment_due=next_due,
        height_cm=_round2(measurement_values.get("height_cm")),
        weight_kg=_round2(measurement_values.get("weight_kg")),
        bmi=results["bmi"],
        body_fat_pct=results["body_fat_pct"],
        lean_mass_kg=results["lean_mass_kg"],
        fat_mass_kg=results["fat_mass_kg"],
        muscle_mass_kg=results["muscle_mass_kg"],
        waist_hip_ratio=results["waist_hip_ratio"],
        basal_metabolic_rate=results["basal_metabolic_rate"],
        waist_cm=_round2(measurement_values.get("waist_cm")),
        hip_cm=_round2(measurement_values.get("hip_cm")),
        chest_cm=_round2(measurement_values.get("chest_cm")),
        arm_cm=_round2(
            measurement_values.get("arm_cm")
            or measurement_values.get("right_arm_relaxed_cm")
            or measurement_values.get("right_arm_flexed_cm")
        ),
        thigh_cm=_round2(measurement_values.get("thigh_cm") or measurement_values.get("right_thigh_cm")),
        observations=_as_dict(payload).get("observations"),
        extra_data={
            "assessment_method": ASSESSMENT_METHOD,
            "record_origin": RECORD_ORIGIN,
            "unavailable_metrics": snapshot["unavailable_metrics"],
            "perimetry_evolution": perimetry_evolution,
        },
        assessment_method=ASSESSMENT_METHOD,
        record_origin=RECORD_ORIGIN,
        sex_used_for_formula=snapshot["inputs"]["sex_used_for_formula"],
        age_used_for_formula=int(snapshot["inputs"]["age_used_for_formula"]),
        height_used_for_formula=_round2(Decimal(snapshot["inputs"]["height_used_for_formula"])),
        weight_used_for_formula=_round2(Decimal(snapshot["inputs"]["weight_used_for_formula"])),
        measurement_protocol=preview["protocol"]["key"],
        formula_version=preview["formula_version"],
        calculation_hash=preview["calculation_hash"],
        idempotency_key=idempotency_key,
        anthropometry_snapshot_json=snapshot,
    )
    db.add(assessment)
    db.flush()
    ensure_anthropometry_ladder_tasks(
        db,
        member=member,
        assessment=assessment,
        evaluator_id=evaluator_id,
        commit=False,
    )
    prepare_anthropometric_assessment_sync_attempt(
        db,
        member=member,
        assessment=assessment,
    )
    if commit:
        db.commit()
        db.refresh(assessment)
    else:
        db.flush()
    return assessment


def ensure_anthropometry_ladder_tasks(
    db: Session,
    *,
    member: Member,
    assessment: Assessment,
    evaluator_id: UUID | None,
    commit: bool = True,
) -> list[Task]:
    assessment_date = _normalize_datetime(getattr(assessment, "assessment_date", None))
    next_due = getattr(assessment, "next_assessment_due", None)
    due_d90 = datetime.combine(next_due, assessment_date.timetz()) if isinstance(next_due, date) else assessment_date + timedelta(days=90)
    if due_d90.tzinfo is None:
        due_d90 = due_d90.replace(tzinfo=timezone.utc)
    member_name = getattr(member, "full_name", "Aluno") or "Aluno"
    first_name = member_name.split()[0] if member_name else "Aluno"
    base_extra = {
        "domain": "trainer",
        "assessment_id": str(assessment.id),
        "assessment_source_id": str(assessment.id),
        "assessment_source_type": ASSESSMENT_METHOD,
        "assessment_method": ASSESSMENT_METHOD,
        "record_origin": RECORD_ORIGIN,
        "assessment_number": getattr(assessment, "assessment_number", None),
        "owner_role": "coach",
        "preferred_shift": getattr(member, "preferred_shift", None),
    }
    specs = [
        {
            "source": "anthropometry_training_delivery_check_d8",
            "technical_ladder_step": "anthropometry_training_delivery_check_d8",
            "day_offset": 8,
            "due_date": assessment_date + timedelta(days=8),
            "priority": TaskPriority.HIGH,
            "title": f"Verificar treino D+8 - {member_name}",
            "description": "Verificar entrega e adequacao do treino apos avaliacao antropometrica.",
            "suggested_message": f"Oi, {first_name}! Passando para confirmar se o treino ficou claro depois da avaliacao.",
        },
        {
            "source": "anthropometry_feedback_d14",
            "technical_ladder_step": "anthropometry_feedback_d14",
            "day_offset": 14,
            "due_date": assessment_date + timedelta(days=14),
            "priority": TaskPriority.MEDIUM,
            "title": f"Registrar feedback D+14 - {member_name}",
            "description": "Registrar feedback de aderencia, desconfortos e ajustes iniciais do treino.",
            "suggested_message": f"Oi, {first_name}! Quero entender como voce esta se sentindo com o treino apos a avaliacao.",
        },
        {
            "source": "anthropometry_rebooking_contact_d75",
            "technical_ladder_step": "anthropometry_rebooking_contact_d75",
            "day_offset": 75,
            "due_date": assessment_date + timedelta(days=75),
            "priority": TaskPriority.MEDIUM,
            "title": f"Iniciar contato de reavaliacao D+75 - {member_name}",
            "description": "Iniciar contato para agendar a reavaliacao prevista no ciclo antropometrico.",
            "suggested_message": f"Oi, {first_name}! Sua reavaliacao esta chegando. Vamos reservar um horario?",
        },
        {
            "source": "anthropometry_reassessment_due_d90",
            "technical_ladder_step": "anthropometry_reassessment_due_d90",
            "day_offset": 90,
            "due_date": due_d90,
            "priority": TaskPriority.MEDIUM,
            "title": f"Reavaliacao antropometrica prevista - {member_name}",
            "description": "Vencimento previsto da nova avaliacao antropometrica.",
            "suggested_message": f"Oi, {first_name}! Hoje fecha a janela prevista da sua reavaliacao. Vamos atualizar suas medidas?",
        },
    ]

    created_or_existing: list[Task] = []
    for spec in specs:
        existing = db.scalar(
            select(Task).where(
                Task.member_id == member.id,
                Task.deleted_at.is_(None),
                Task.extra_data["source"].astext == spec["source"],
                Task.extra_data["assessment_id"].astext == str(assessment.id),
            )
        )
        if existing is not None:
            created_or_existing.append(existing)
            continue
        extra_data = {
            **base_extra,
            "source": spec["source"],
            "day_offset": spec["day_offset"],
            "technical_ladder_step": spec["technical_ladder_step"],
            "primary_action_label": "Agendar reavaliacao" if spec["day_offset"] >= 75 else "Registrar acompanhamento",
            "work_queue_visible_from": spec["due_date"].isoformat(),
        }
        task = Task(
            gym_id=getattr(member, "gym_id", None) or getattr(assessment, "gym_id"),
            member_id=member.id,
            assigned_to_user_id=evaluator_id,
            title=spec["title"],
            description=spec["description"],
            priority=spec["priority"],
            status=TaskStatus.TODO,
            kanban_column=TaskStatus.TODO.value,
            due_date=spec["due_date"],
            suggested_message=spec["suggested_message"],
            extra_data=extra_data,
        )
        db.add(task)
        created_or_existing.append(task)
    invalidate_dashboard_cache("tasks")
    if commit:
        db.commit()
    else:
        db.flush()
    return created_or_existing


def get_anthropometric_assessment_or_404(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
    assessment_id: UUID,
) -> Assessment:
    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.gym_id == gym_id,
            Assessment.member_id == member_id,
            Assessment.assessment_method == ASSESSMENT_METHOD,
            Assessment.deleted_at.is_(None),
        )
    )
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliacao antropometrica nao encontrada")
    return assessment


def list_anthropometric_assessment_report_history(
    db: Session,
    *,
    gym_id: UUID,
    member_id: UUID,
) -> list[Assessment]:
    return list(
        db.scalars(
            select(Assessment)
            .where(
                Assessment.gym_id == gym_id,
                Assessment.member_id == member_id,
                Assessment.assessment_method == ASSESSMENT_METHOD,
                Assessment.deleted_at.is_(None),
            )
            .order_by(Assessment.assessment_date.asc(), Assessment.created_at.asc())
        ).all()
    )


def build_history_assessment_item(assessment: Assessment, *, comparison_warning: str | None = None) -> Any:
    method = getattr(assessment, "assessment_method", None)
    origin = getattr(assessment, "record_origin", None)
    if method == ASSESSMENT_METHOD:
        badge = "Antropometria"
    elif origin == "legacy" or method is None:
        badge = "Avaliacao anterior/legada"
    else:
        badge = "Avaliacao anterior/legada"
    setattr(assessment, "history_badge", badge)
    setattr(assessment, "comparison_warning", comparison_warning)
    return assessment


def build_bioimpedance_history_item(evaluation: Any, *, comparison_warning: str | None = None) -> Any:
    measured_at = getattr(evaluation, "measured_at", None)
    if not isinstance(measured_at, datetime):
        evaluation_date = getattr(evaluation, "evaluation_date", None)
        measured_at = datetime.combine(evaluation_date, datetime.min.time(), tzinfo=timezone.utc) if isinstance(evaluation_date, date) else None
    body_fat_pct = getattr(evaluation, "body_fat_used_percent", None) or getattr(evaluation, "body_fat_percent", None)
    lean_mass = getattr(evaluation, "fat_free_mass_kg", None) or getattr(evaluation, "lean_mass_kg", None)
    return _HistoryItem(
        id=getattr(evaluation, "id"),
        gym_id=getattr(evaluation, "gym_id", None),
        member_id=getattr(evaluation, "member_id", None),
        evaluator_id=getattr(evaluation, "reviewer_user_id", None),
        assessment_number=None,
        assessment_date=measured_at or datetime.now(tz=timezone.utc),
        next_assessment_due=getattr(evaluation, "next_assessment_due", None),
        height_cm=getattr(evaluation, "height_cm", None),
        weight_kg=getattr(evaluation, "weight_kg", None),
        bmi=getattr(evaluation, "bmi", None),
        body_fat_pct=body_fat_pct,
        lean_mass_kg=lean_mass,
        fat_mass_kg=getattr(evaluation, "body_fat_kg", None) or getattr(evaluation, "fat_mass_estimated_kg", None),
        muscle_mass_kg=getattr(evaluation, "muscle_mass_kg", None) or getattr(evaluation, "skeletal_muscle_kg", None),
        waist_hip_ratio=getattr(evaluation, "waist_hip_ratio", None),
        basal_metabolic_rate=getattr(evaluation, "basal_metabolic_rate_kcal", None),
        assessment_method="bioimpedance",
        record_origin="cordex",
        sex_used_for_formula=getattr(evaluation, "sex", None),
        age_used_for_formula=getattr(evaluation, "age_years", None),
        height_used_for_formula=getattr(evaluation, "height_cm", None),
        weight_used_for_formula=getattr(evaluation, "weight_kg", None),
        measurement_protocol=getattr(evaluation, "measurement_protocol", None),
        formula_version=None,
        calculation_hash=None,
        anthropometry_snapshot_json=None,
        history_badge="Bioimpedancia",
        comparison_warning=comparison_warning,
        waist_cm=getattr(evaluation, "waist_cm", None),
        hip_cm=getattr(evaluation, "hip_cm", None),
        chest_cm=getattr(evaluation, "chest_cm", None),
        arm_cm=getattr(evaluation, "right_arm_relaxed_cm", None),
        thigh_cm=getattr(evaluation, "right_thigh_cm", None),
        resting_hr=None,
        blood_pressure_systolic=None,
        blood_pressure_diastolic=None,
        vo2_estimated=None,
        strength_score=None,
        flexibility_score=None,
        cardio_score=None,
        observations=getattr(evaluation, "notes", None),
        ai_analysis=getattr(evaluation, "ai_coach_summary", None),
        ai_recommendations=None,
        ai_risk_flags=None,
        extra_data={"assessment_method": "bioimpedance", "source_evaluation_id": str(getattr(evaluation, "id"))},
        created_at=getattr(evaluation, "created_at", measured_at or datetime.now(tz=timezone.utc)),
        updated_at=getattr(evaluation, "updated_at", measured_at or datetime.now(tz=timezone.utc)),
    )


class _HistoryItem:
    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_unset=True)
    return dict(value)


def _normalize_datetime(value: Any) -> datetime:
    if value is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="assessment_date_invalid")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _resolve_sex(data: dict[str, Any], member: Member | None) -> str:
    sex = data.get("sex_for_formula") or (getattr(member, "sex_for_clinical_calculation", None) if member is not None else None)
    if sex not in {"male", "female"}:
        _raise_unprocessable("sex_for_formula_required", {})
    return str(sex)


def _resolve_age(data: dict[str, Any], member: Member | None, assessment_date: datetime) -> int:
    if data.get("age_years") is not None:
        years = int(data["age_years"])
        if years <= 0:
            _raise_unprocessable("age_must_be_positive", {})
        return years
    birthdate = getattr(member, "birthdate", None) if member is not None else None
    if not isinstance(birthdate, date):
        _raise_unprocessable("age_or_birthdate_required", {})
    years = assessment_date.date().year - birthdate.year
    if (assessment_date.date().month, assessment_date.date().day) < (birthdate.month, birthdate.day):
        years -= 1
    if years <= 0:
        _raise_unprocessable("age_must_be_positive", {})
    return years


def _consolidate_measurements(raw: dict[str, Any], *, required_fields: set[str]) -> dict[str, dict[str, Any]]:
    consolidated: dict[str, dict[str, Any]] = {}
    for field, raw_measurement in raw.items():
        measurement = _as_dict(raw_measurement)
        attempts = [_to_decimal(value) for value in measurement.get("attempts") or []]
        if len(attempts) < 2 or len(attempts) > 3:
            _raise_unprocessable("measurement_attempt_count_invalid", {"field": field})
        unit = str(measurement.get("unit") or "")
        expected_unit = _expected_unit(field)
        if unit != expected_unit:
            _raise_unprocessable("measurement_unit_invalid", {"field": field, "expected": expected_unit})
        side = str(measurement.get("side") or "right")
        reason = (measurement.get("side_exception_reason") or "").strip() or None
        if _requires_body_side(field):
            expected_side = _expected_body_side(field)
            if side != expected_side and not reason:
                _raise_unprocessable("side_exception_reason_required", {"field": field, "side": side})
        else:
            side = "not_applicable"
        for attempt in attempts:
            _validate_decimal_precision(field, attempt)
            _validate_range(field, attempt)
        official, consolidation = _official_value(field, attempts)
        consolidated[field] = {
            "decimal_value": official,
            "attempts": attempts,
            "unit": unit,
            "side": side,
            "side_exception_reason": reason,
            "consolidation": consolidation,
            "required_for_formula": field in required_fields,
        }
    for field in required_fields:
        if field not in consolidated:
            continue
    return consolidated


def _profile_measurement(field: str, value: Any) -> dict[str, Any]:
    decimal_value = _to_decimal(value)
    _validate_range(field, decimal_value)
    return {
        "decimal_value": decimal_value,
        "attempts": [decimal_value],
        "unit": _expected_unit(field),
        "side": "not_applicable",
        "side_exception_reason": None,
        "consolidation": "profile_snapshot",
        "required_for_formula": True,
    }


def _official_value(field: str, attempts: list[Decimal]) -> tuple[Decimal, str]:
    if len(attempts) == 2:
        first, second = attempts
        mean = (first + second) / Decimal("2")
        if mean == 0:
            _raise_unprocessable("implausible_measurement", {"field": field})
        relative_diff = abs(first - second) / mean * Decimal("100")
        if relative_diff > _tolerance_percent(field):
            _raise_unprocessable("third_attempt_required", {"field": field, "tolerance_percent": str(_tolerance_percent(field))})
        return mean, "mean"
    sorted_attempts = sorted(attempts)
    return sorted_attempts[1], "median"


def _expected_unit(field: str) -> str:
    if field == "weight_kg":
        return "kg"
    if field.endswith("_mm"):
        return "mm"
    return "cm"


def _requires_body_side(field: str) -> bool:
    return field.endswith("_mm") or field.endswith("_cm") and field != "height_cm"


def _expected_body_side(field: str) -> str:
    if field.startswith("left_"):
        return "left"
    return "right"


def _tolerance_percent(field: str) -> Decimal:
    return Decimal("5") if field.endswith("_mm") else Decimal("1")


def _validate_range(field: str, value: Decimal) -> None:
    if field == "height_cm":
        minimum, maximum = Decimal("80.0"), Decimal("250.0")
    elif field == "weight_kg":
        minimum, maximum = Decimal("15.0"), Decimal("400.0")
    elif field.endswith("_mm"):
        minimum, maximum = Decimal("1.0"), Decimal("80.0")
    else:
        minimum, maximum = Decimal("10.0"), Decimal("300.0")
    if value < minimum or value > maximum:
        _raise_unprocessable("implausible_measurement", {"field": field, "minimum": str(minimum), "maximum": str(maximum)})


def _validate_decimal_precision(field: str, value: Decimal) -> None:
    if value != value.quantize(_Q1):
        _raise_unprocessable("measurement_precision_invalid", {"field": field, "precision": "0.1"})


def _calculate_bmi(height_cm: Decimal, weight_kg: Decimal) -> Decimal:
    height_m = height_cm / Decimal("100")
    return _round2(weight_kg / (height_m * height_m))


def _calculate_waist_hip_ratio(measurements: dict[str, dict[str, Any]]) -> Decimal | None:
    waist = measurements.get("waist_cm", {}).get("decimal_value")
    hip = measurements.get("hip_cm", {}).get("decimal_value")
    if waist is None or hip is None or hip == 0:
        return None
    return _round2(waist / hip)


def _calculate_mifflin_bmr(*, sex: str, age_years: int, height_cm: Decimal, weight_kg: Decimal) -> Decimal | None:
    if age_years <= 0:
        return None
    sex_constant = Decimal("5") if sex == "male" else Decimal("-161")
    return _round2(Decimal("10") * weight_kg + Decimal("6.25") * height_cm - Decimal("5") * Decimal(age_years) + sex_constant)


def _calculate_lee_muscle_mass(
    *,
    sex: str,
    age_years: int,
    height_cm: Decimal,
    ethnicity: str,
    measurements: dict[str, dict[str, Any]],
) -> Decimal:
    pi = Decimal(str(math.pi))
    arm = measurements["right_arm_relaxed_cm"]["decimal_value"]
    thigh = measurements["right_thigh_cm"]["decimal_value"]
    calf = measurements["right_calf_cm"]["decimal_value"]
    triceps_cm = measurements["skinfold_triceps_mm"]["decimal_value"] / Decimal("10")
    thigh_fold_cm = measurements["skinfold_thigh_mm"]["decimal_value"] / Decimal("10")
    calf_fold_cm = measurements["skinfold_calf_mm"]["decimal_value"] / Decimal("10")
    corrected_arm = arm - pi * triceps_cm
    corrected_thigh = thigh - pi * thigh_fold_cm
    corrected_calf = calf - pi * calf_fold_cm
    if min(corrected_arm, corrected_thigh, corrected_calf) <= 0:
        _raise_unprocessable("lee_corrected_circumference_invalid", {})
    sex_coefficient = Decimal("1") if sex == "male" else Decimal("0")
    ethnicity_coefficient = {
        "asian": Decimal("-2.0"),
        "black": Decimal("1.1"),
        "white": Decimal("0"),
    }[ethnicity]
    height_m = height_cm / Decimal("100")
    result = (
        height_m
        * (
            Decimal("0.00744") * corrected_arm**2
            + Decimal("0.00088") * corrected_thigh**2
            + Decimal("0.00441") * corrected_calf**2
        )
        + Decimal("2.4") * sex_coefficient
        - Decimal("0.048") * Decimal(age_years)
        + ethnicity_coefficient
        + Decimal("7.8")
    )
    if result <= 0:
        _raise_unprocessable("lee_muscle_mass_invalid", {})
    return _round2(result) or Decimal("0")


def _lee_snapshot(
    *,
    enabled: bool,
    result: Decimal | None,
    ethnicity: str | None,
    sex: str,
    age_years: int,
    measurements: dict[str, dict[str, Any]],
    flags: list[str],
) -> dict[str, Any]:
    if not enabled:
        return {"enabled": False, "formula_version": None, "result_kg": None, "flags": []}
    pi = Decimal(str(math.pi))

    def corrected(circumference: str, skinfold: str) -> Decimal:
        return measurements[circumference]["decimal_value"] - pi * measurements[skinfold]["decimal_value"] / Decimal("10")

    return {
        "enabled": True,
        "formula_version": LEE_FORMULA_VERSION,
        "formula": (
            "height_m*(0.00744*CAG^2+0.00088*CTG^2+0.00441*CCG^2)"
            "+2.4*sex-0.048*age+ethnicity+7.8"
        ),
        "circumference_correction": "circumference_cm-pi*(skinfold_mm/10)",
        "measurement_side": "right",
        "sex_coefficient": "1" if sex == "male" else "0",
        "ethnicity": ethnicity,
        "ethnicity_coefficient": {"asian": "-2.0", "black": "1.1", "white": "0"}.get(ethnicity),
        "age_years": age_years,
        "coefficients": {
            "arm": "0.00744",
            "thigh": "0.00088",
            "calf": "0.00441",
            "sex": "2.4",
            "age": "-0.048",
            "constant": "7.8",
        },
        "corrected_circumferences_cm": {
            "arm": _decimal_str(corrected("right_arm_relaxed_cm", "skinfold_triceps_mm")),
            "thigh": _decimal_str(corrected("right_thigh_cm", "skinfold_thigh_mm")),
            "calf": _decimal_str(corrected("right_calf_cm", "skinfold_calf_mm")),
        },
        "result_kg": _decimal_str(result),
        "flags": flags,
    }


def _snapshot_measurement(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "attempts": [_decimal_str(item, one_decimal=True) for item in value["attempts"]],
        "unit": value["unit"],
        "side": value["side"],
        "side_exception_reason": value["side_exception_reason"],
        "consolidated_value": _decimal_str(value["decimal_value"], one_decimal=True),
        "consolidation": value["consolidation"],
        "required_for_formula": value["required_for_formula"],
    }


def _snapshot_results(results: dict[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for key, value in results.items():
        snapshot[key] = _decimal_str(value) if isinstance(value, Decimal) else value
    return snapshot


def _extract_perimetry_evolution_values(measurement_values: dict[str, Decimal]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in _PERIMETRY_EVOLUTION_FIELDS:
        value = measurement_values.get(field)
        if value is not None:
            values[field] = _decimal_str(value, one_decimal=True) or ""
    return values


def _round2(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(_Q2, rounding=ROUND_HALF_UP)


def _blocking_protocol_flags(flags: list[str] | tuple[str, ...]) -> list[str]:
    return [flag for flag in flags if flag not in _WARNING_ONLY_PROTOCOL_FLAGS]


def _to_decimal(value: Any) -> Decimal:
    try:
        decimal_value = parse_localized_decimal(value)
    except LocalizedNumberError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "measurement_value_invalid", "value": value},
        ) from exc
    if decimal_value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "measurement_value_invalid", "value": value},
        )
    return decimal_value


def _decimal_str(value: Decimal | None, *, one_decimal: bool = False) -> str | None:
    if value is None:
        return None
    if one_decimal:
        return format(value.quantize(_Q1), "f")
    return format(value.quantize(_Q2), "f")


def _raise_unprocessable(code: str, context: dict[str, Any]) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": code, **context},
    )
