from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable


SKINFOLD_FIELDS = (
    "skinfold_chest_mm",
    "skinfold_midaxillary_mm",
    "skinfold_subscapular_mm",
    "skinfold_triceps_mm",
    "skinfold_biceps_mm",
    "skinfold_abdominal_mm",
    "skinfold_suprailiac_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
)


@dataclass(frozen=True)
class BodyCompositionProtocol:
    key: str
    label: str
    sex: str | None
    age_min: int | None
    age_max: int | None
    required_fields: tuple[str, ...]
    calculation: str | None
    supported: bool
    notes: str = ""


PROTOCOLS: tuple[BodyCompositionProtocol, ...] = (
    BodyCompositionProtocol(
        key="manual_bioimpedance",
        label="Adicionar manualmente (Balanca de Bioimpedancia)",
        sex=None,
        age_min=None,
        age_max=None,
        required_fields=(),
        calculation=None,
        supported=False,
        notes="Catalog option only; use raw bioimpedance/manual override.",
    ),
    BodyCompositionProtocol(
        key="mcardle_1992_4_male_18_34",
        label="Macardle (1992) 4 dobras - Homens, 18-34 anos",
        sex="male",
        age_min=18,
        age_max=34,
        required_fields=("skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_triceps_mm", "skinfold_thigh_mm"),
        calculation="ymca_4",
        supported=True,
        notes="Macardle/YMCA adulto 4 dobras; resultado direto em percentual.",
    ),
    BodyCompositionProtocol(
        key="mcardle_1992_3_female_18_48",
        label="Macardle (1992) 3 dobras - Mulheres, 18-48 anos",
        sex="female",
        age_min=18,
        age_max=48,
        required_fields=("skinfold_abdominal_mm", "skinfold_triceps_mm", "skinfold_suprailiac_mm"),
        calculation="ymca_3",
        supported=True,
        notes="Macardle/YMCA adulto 3 dobras; resultado direto em percentual.",
    ),
    BodyCompositionProtocol(
        key="jackson_pollock_7_female_18_55",
        label="Jackson et al. (1980), 7 dobras - Mulheres negras ou hispanicas, 18-55 anos",
        sex="female",
        age_min=18,
        age_max=55,
        required_fields=(
            "skinfold_chest_mm",
            "skinfold_midaxillary_mm",
            "skinfold_subscapular_mm",
            "skinfold_triceps_mm",
            "skinfold_abdominal_mm",
            "skinfold_suprailiac_mm",
            "skinfold_thigh_mm",
        ),
        calculation="jackson_pollock_7",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="jackson_pollock_7_male_18_61",
        label="Jackson e Pollock (1978), 7 dobras - Homens negros ou atletas, 18-61 anos",
        sex="male",
        age_min=18,
        age_max=61,
        required_fields=(
            "skinfold_chest_mm",
            "skinfold_midaxillary_mm",
            "skinfold_subscapular_mm",
            "skinfold_triceps_mm",
            "skinfold_abdominal_mm",
            "skinfold_suprailiac_mm",
            "skinfold_thigh_mm",
        ),
        calculation="jackson_pollock_7",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="jackson_pollock_3_female_18_55",
        label="Jackson et al. (1980), 3 dobras - Mulheres brancas, 18-55 anos",
        sex="female",
        age_min=18,
        age_max=55,
        required_fields=("skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"),
        calculation="jackson_pollock_3",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="jackson_pollock_3_male_18_61",
        label="Jackson e Pollock (1978), 3 dobras - Homens brancos, 18-61 anos",
        sex="male",
        age_min=18,
        age_max=61,
        required_fields=("skinfold_chest_mm", "skinfold_abdominal_mm", "skinfold_thigh_mm"),
        calculation="jackson_pollock_3",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="pollock_1980_7_female_18_61",
        label="Pollock et al. (1980), 7 dobras - Mulheres adultas, 18-61 anos",
        sex="female",
        age_min=18,
        age_max=61,
        required_fields=(
            "skinfold_chest_mm",
            "skinfold_midaxillary_mm",
            "skinfold_subscapular_mm",
            "skinfold_triceps_mm",
            "skinfold_abdominal_mm",
            "skinfold_suprailiac_mm",
            "skinfold_thigh_mm",
        ),
        calculation="jackson_pollock_7",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="pollock_1980_7_male_18_61",
        label="Pollock et al. (1980), 7 dobras - Homens adultos, 18-61 anos",
        sex="male",
        age_min=18,
        age_max=61,
        required_fields=(
            "skinfold_chest_mm",
            "skinfold_midaxillary_mm",
            "skinfold_subscapular_mm",
            "skinfold_triceps_mm",
            "skinfold_abdominal_mm",
            "skinfold_suprailiac_mm",
            "skinfold_thigh_mm",
        ),
        calculation="jackson_pollock_7",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="guedes_1985_3_female_18_30",
        label="Guedes (1985), 3 dobras - Mulheres, 18-30 anos",
        sex="female",
        age_min=18,
        age_max=30,
        required_fields=("skinfold_subscapular_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"),
        calculation="guedes_1985_3",
        supported=True,
        notes="Densidade corporal Guedes adulto 3 dobras; convertido por Siri.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_3_male_18_30",
        label="Guedes (1985), 3 dobras - Homens, 18-30 anos",
        sex="male",
        age_min=18,
        age_max=30,
        required_fields=("skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_abdominal_mm"),
        calculation="guedes_1985_3",
        supported=True,
        notes="Densidade corporal Guedes adulto 3 dobras; convertido por Siri.",
    ),
    BodyCompositionProtocol(
        key="petroski_1995_female_18_51",
        label="Petroski (1995), Mulheres, 18-51 anos",
        sex="female",
        age_min=18,
        age_max=51,
        required_fields=("skinfold_midaxillary_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm", "skinfold_calf_mm", "weight_kg", "height_cm"),
        calculation="petroski_1995_female_4",
        supported=True,
        notes="Densidade corporal Petroski feminino 4 dobras; convertido por Siri.",
    ),
    BodyCompositionProtocol(
        key="petroski_1995_male_18_66",
        label="Petroski (1995), Homens, 18-66 anos",
        sex="male",
        age_min=18,
        age_max=66,
        required_fields=("skinfold_subscapular_mm", "skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_calf_mm"),
        calculation="petroski_1995_male_4",
        supported=True,
        notes="Densidade corporal Petroski masculino 4 dobras; convertido por Siri.",
    ),
    BodyCompositionProtocol(
        key="durnin_womersley_1974_female_18_68",
        label="Durnin & Womersley (1974), Mulheres, 18-68 anos. Generalizada",
        sex="female",
        age_min=18,
        age_max=68,
        required_fields=("skinfold_triceps_mm", "skinfold_biceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm"),
        calculation="durnin_womersley_4",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="durnin_womersley_1974_male_17_72",
        label="Durnin & Womersley (1974), Homens, 17-72 anos. Generalizada",
        sex="male",
        age_min=17,
        age_max=72,
        required_fields=("skinfold_triceps_mm", "skinfold_biceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm"),
        calculation="durnin_womersley_4",
        supported=True,
    ),
    BodyCompositionProtocol(
        key="weltman_1988_female_obese_20_60",
        label="Weltman et col. (1988), Mulheres obesas, 20-60 anos",
        sex="female",
        age_min=20,
        age_max=60,
        required_fields=("abdomen_cm", "weight_kg", "height_cm"),
        calculation="weltman_1988_female",
        supported=True,
        notes="Weltman feminino usa abdomen, peso e altura; resultado direto em percentual.",
    ),
    BodyCompositionProtocol(
        key="weltman_1988_male_obese_20_60",
        label="Weltman et col. (1988), Homens obesos, 20-60 anos",
        sex="male",
        age_min=20,
        age_max=60,
        required_fields=("waist_cm", "weight_kg"),
        calculation=None,
        supported=False,
        notes="Manual-only: a equacao masculina publicada usa circunferencia iliaca, campo ainda nao capturado pelo Cordex.",
    ),
    BodyCompositionProtocol(
        key="slaughter_1988_boys_black_white_6_17",
        label="Slaughter et al. (1988), Meninos negros ou brancos, 6-17 anos",
        sex="male",
        age_min=6,
        age_max=17,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Requires maturity/race branch not captured in V1.",
    ),
    BodyCompositionProtocol(
        key="slaughter_1988_girls_black_white_6_17",
        label="Slaughter et al. (1988), Meninas negras ou brancas, 6-17 anos",
        sex="female",
        age_min=6,
        age_max=17,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Requires maturity/race branch not captured in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_boys_white_prepuberal_6_11",
        label="Guedes (1985), Rapazes brancos pre-pubere, 6-11 anos",
        sex="male",
        age_min=6,
        age_max=11,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_boys_white_puberal_12_16",
        label="Guedes (1985), Rapazes brancos pubere, 12-16 anos",
        sex="male",
        age_min=12,
        age_max=16,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_boys_white_postpuberal_17_18",
        label="Guedes (1985), Rapazes brancos pos-pubere, 17-18 anos",
        sex="male",
        age_min=17,
        age_max=18,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_boys_black_prepuberal_6_11",
        label="Guedes (1985), Rapazes negros pre-pubere, 6-11 anos",
        sex="male",
        age_min=6,
        age_max=11,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_boys_black_puberal_12_16",
        label="Guedes (1985), Rapazes negros pubere, 12-16 anos",
        sex="male",
        age_min=12,
        age_max=16,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_boys_black_postpuberal_17_18",
        label="Guedes (1985), Rapazes negros pos-pubere, 17-18 anos",
        sex="male",
        age_min=17,
        age_max=18,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="guedes_1985_girls_sum_under_35",
        label="Guedes (1985), Mocas (Soma das dobras < 35mm)",
        sex="female",
        age_min=6,
        age_max=18,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="slaughter_1988_boys",
        label="Slaughter et al. (1988), Meninos",
        sex="male",
        age_min=6,
        age_max=17,
        required_fields=("skinfold_triceps_mm", "skinfold_calf_mm"),
        calculation="slaughter_2sites_simple",
        supported=True,
        notes="Slaughter simples 2 dobras com triceps e panturrilha; variantes por raca/maturacao permanecem manual-only.",
    ),
    BodyCompositionProtocol(
        key="slaughter_1988_girls",
        label="Slaughter et al. (1988), Meninas",
        sex="female",
        age_min=6,
        age_max=17,
        required_fields=("skinfold_triceps_mm", "skinfold_calf_mm"),
        calculation="slaughter_2sites_simple",
        supported=True,
        notes="Slaughter simples 2 dobras com triceps e panturrilha; variantes por raca/maturacao permanecem manual-only.",
    ),
    BodyCompositionProtocol(
        key="mcardle_1992_female_9_12",
        label="Macardle (1992), Mulheres, 9-12 anos",
        sex="female",
        age_min=9,
        age_max=12,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="mcardle_1992_female_13_16",
        label="Macardle (1992), Mulheres, 13-16 anos",
        sex="female",
        age_min=13,
        age_max=16,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="mcardle_1992_male_9_12",
        label="Macardle (1992), Homens, 9-12 anos",
        sex="male",
        age_min=9,
        age_max=12,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="mcardle_1992_male_13_16",
        label="Macardle (1992), Homens, 13-16 anos",
        sex="male",
        age_min=13,
        age_max=16,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm"),
        calculation=None,
        supported=False,
        notes="Listed for operational parity; formula not implemented in V1.",
    ),
    BodyCompositionProtocol(
        key="faulkner_1968_male_20_30",
        label="Faulkner (1968), Homens, 20-30 anos",
        sex="male",
        age_min=20,
        age_max=30,
        required_fields=("skinfold_triceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm", "skinfold_abdominal_mm"),
        calculation="faulkner_1968_4",
        supported=True,
        notes="Faulkner/Yuhasz modificado 4 dobras; resultado direto em percentual.",
    ),
)


PROTOCOL_BY_KEY = {protocol.key: protocol for protocol in PROTOCOLS}


def get_protocol(key: str | None) -> BodyCompositionProtocol | None:
    if not key:
        return None
    return PROTOCOL_BY_KEY.get(key)


def protocol_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": protocol.key,
            "label": protocol.label,
            "sex": protocol.sex,
            "age_min": protocol.age_min,
            "age_max": protocol.age_max,
            "required_fields": list(protocol.required_fields),
            "supported": protocol.supported,
            "notes": protocol.notes,
        }
        for protocol in PROTOCOLS
    ]


def calculate_protocol_body_fat(values: Any) -> dict[str, Any]:
    key = _read(values, "measurement_protocol")
    protocol = get_protocol(key)
    flags: list[str] = []
    missing_fields: list[str] = []

    if protocol is None:
        return _empty_result(flags=[], missing_fields=[])

    if not protocol.supported or protocol.calculation is None:
        return _empty_result(
            flags=["anthropometry_protocol_manual_only"],
            missing_fields=[],
            protocol=protocol,
        )

    sex = _read(values, "sex")
    age_years = _read_int(values, "age_years")
    weight_kg = _read_float(values, "weight_kg")

    if protocol.sex and sex and protocol.sex != sex:
        flags.append("anthropometry_protocol_mismatch")
    elif protocol.sex and not sex:
        missing_fields.append("sexo")

    if age_years is None:
        missing_fields.append("idade")
    elif protocol.age_min is not None and protocol.age_max is not None and not protocol.age_min <= age_years <= protocol.age_max:
        flags.append("anthropometry_protocol_age_outside_range")

    for field in protocol.required_fields:
        value = _read_float(values, field)
        if value is None:
            missing_fields.append(_field_label(field))
        elif not _is_plausible_field_value(field, value):
            flags.append("impossible_measurement_value")

    if "impossible_measurement_value" in flags or "anthropometry_protocol_mismatch" in flags or missing_fields:
        if missing_fields:
            flags.append("anthropometry_incomplete")
        return _empty_result(flags=flags, missing_fields=missing_fields, protocol=protocol)

    calculator = _CALCULATORS.get(protocol.calculation)
    percent = calculator(values, sex, age_years) if calculator else None
    if percent is None or not 2 <= percent <= 75:
        flags.append("impossible_measurement_value")
        return _empty_result(flags=flags, missing_fields=missing_fields, protocol=protocol)

    confidence = "medium"
    if "anthropometry_protocol_age_outside_range" in flags:
        confidence = "low"
    range_min, range_max = _estimated_range(percent, confidence)
    fat_mass = None
    lean_mass = None
    if weight_kg is not None:
        fat_mass = round(weight_kg * percent / 100, 2)
        lean_mass = round(weight_kg - fat_mass, 2)

    return {
        "protocol_key": protocol.key,
        "protocol_label": protocol.label,
        "body_fat_percent": _round_percent(percent),
        "method": "skinfold_protocol",
        "confidence": confidence,
        "range_min": range_min,
        "range_max": range_max,
        "fat_mass_kg": fat_mass,
        "lean_mass_kg": lean_mass,
        "flags": list(dict.fromkeys(flags)),
        "missing_fields": missing_fields,
        "required_fields": list(protocol.required_fields),
        "supported": True,
    }


def _empty_result(
    *,
    flags: list[str],
    missing_fields: list[str],
    protocol: BodyCompositionProtocol | None = None,
) -> dict[str, Any]:
    return {
        "protocol_key": protocol.key if protocol else None,
        "protocol_label": protocol.label if protocol else None,
        "body_fat_percent": None,
        "method": None,
        "confidence": None,
        "range_min": None,
        "range_max": None,
        "fat_mass_kg": None,
        "lean_mass_kg": None,
        "flags": list(dict.fromkeys(flags)),
        "missing_fields": missing_fields,
        "required_fields": list(protocol.required_fields) if protocol else [],
        "supported": bool(protocol and protocol.supported),
    }


def _jackson_pollock_3(values: Any, sex: str | None, age_years: int | None) -> float | None:
    if sex == "male":
        total = _sum_fields(values, ("skinfold_chest_mm", "skinfold_abdominal_mm", "skinfold_thigh_mm"))
        if total is None or age_years is None:
            return None
        density = 1.10938 - 0.0008267 * total + 0.0000016 * total**2 - 0.0002574 * age_years
        return _siri(density)
    if sex == "female":
        total = _sum_fields(values, ("skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"))
        if total is None or age_years is None:
            return None
        density = 1.0994921 - 0.0009929 * total + 0.0000023 * total**2 - 0.0001392 * age_years
        return _siri(density)
    return None


def _jackson_pollock_7(values: Any, sex: str | None, age_years: int | None) -> float | None:
    total = _sum_fields(
        values,
        (
            "skinfold_chest_mm",
            "skinfold_midaxillary_mm",
            "skinfold_subscapular_mm",
            "skinfold_triceps_mm",
            "skinfold_abdominal_mm",
            "skinfold_suprailiac_mm",
            "skinfold_thigh_mm",
        ),
    )
    if total is None or age_years is None:
        return None
    if sex == "male":
        density = 1.112 - 0.00043499 * total + 0.00000055 * total**2 - 0.00028826 * age_years
        return _siri(density)
    if sex == "female":
        density = 1.097 - 0.00046971 * total + 0.00000056 * total**2 - 0.00012828 * age_years
        return _siri(density)
    return None


def _durnin_womersley_4(values: Any, sex: str | None, age_years: int | None) -> float | None:
    total = _sum_fields(values, ("skinfold_triceps_mm", "skinfold_biceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm"))
    if total is None or total <= 0 or age_years is None or sex not in {"male", "female"}:
        return None
    log_sum = math.log10(total)
    constant, multiplier = _durnin_coefficients(sex, age_years)
    density = constant - multiplier * log_sum
    return _siri(density)


def _petroski_1995_male_4(values: Any, sex: str | None, age_years: int | None) -> float | None:
    if sex != "male" or age_years is None:
        return None
    total = _sum_fields(
        values,
        (
            "skinfold_subscapular_mm",
            "skinfold_triceps_mm",
            "skinfold_suprailiac_mm",
            "skinfold_calf_mm",
        ),
    )
    if total is None:
        return None
    density = 1.10726863 - 0.00081201 * total + 0.00000212 * total**2 - 0.00041761 * age_years
    return _siri(density)


def _petroski_1995_female_4(values: Any, sex: str | None, age_years: int | None) -> float | None:
    if sex != "female" or age_years is None:
        return None
    total = _sum_fields(
        values,
        (
            "skinfold_midaxillary_mm",
            "skinfold_suprailiac_mm",
            "skinfold_thigh_mm",
            "skinfold_calf_mm",
        ),
    )
    weight_kg = _read_float(values, "weight_kg")
    height_cm = _read_float(values, "height_cm")
    if total is None or weight_kg is None or height_cm is None:
        return None
    density = (
        1.03465850
        - 0.00063129 * total
        + 0.00000187 * total**2
        - 0.00031165 * age_years
        - 0.00048890 * weight_kg
        + 0.00051345 * height_cm
    )
    return _siri(density)


def _guedes_1985_3(values: Any, sex: str | None, age_years: int | None) -> float | None:
    if sex == "male":
        total = _sum_fields(values, ("skinfold_triceps_mm", "skinfold_abdominal_mm", "skinfold_suprailiac_mm"))
        if total is None or total <= 0:
            return None
        return _siri(1.1714 - 0.0671 * math.log10(total))
    if sex == "female":
        total = _sum_fields(values, ("skinfold_suprailiac_mm", "skinfold_thigh_mm", "skinfold_subscapular_mm"))
        if total is None or total <= 0:
            return None
        return _siri(1.1665 - 0.0706 * math.log10(total))
    return None


def _ymca_4(values: Any, sex: str | None, age_years: int | None) -> float | None:
    total = _sum_fields(values, ("skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_triceps_mm", "skinfold_thigh_mm"))
    if total is None or age_years is None:
        return None
    if sex == "male":
        return 0.29288 * total - 0.0005 * total**2 + 0.15845 * age_years - 5.76377
    if sex == "female":
        return 0.29669 * total - 0.00043 * total**2 + 0.02963 * age_years + 1.4072
    return None


def _ymca_3(values: Any, sex: str | None, age_years: int | None) -> float | None:
    total = _sum_fields(values, ("skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_triceps_mm"))
    if total is None or age_years is None:
        return None
    if sex == "male":
        return 0.39287 * total - 0.00105 * total**2 + 0.15772 * age_years - 5.18845
    if sex == "female":
        return 0.41563 * total - 0.00112 * total**2 + 0.03661 * age_years + 4.03653
    return None


def _weltman_1988_female(values: Any, sex: str | None, age_years: int | None) -> float | None:
    if sex != "female":
        return None
    abdomen_cm = _read_float(values, "abdomen_cm")
    weight_kg = _read_float(values, "weight_kg")
    height_cm = _read_float(values, "height_cm")
    if abdomen_cm is None or weight_kg is None or height_cm is None:
        return None
    return 0.11077 * abdomen_cm - 0.17666 * height_cm + 0.14354 * weight_kg + 51.03301


def _slaughter_2sites_simple(values: Any, sex: str | None, age_years: int | None) -> float | None:
    total = _sum_fields(values, ("skinfold_triceps_mm", "skinfold_calf_mm"))
    if total is None:
        return None
    if sex == "male":
        return 0.735 * total + 1.0
    if sex == "female":
        return 0.610 * total + 5.1
    return None


def _faulkner_1968_4(values: Any, sex: str | None, age_years: int | None) -> float | None:
    total = _sum_fields(values, ("skinfold_triceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm", "skinfold_abdominal_mm"))
    if total is None:
        return None
    return 5.783 + 0.153 * total


_CALCULATORS: dict[str, Callable[[Any, str | None, int | None], float | None]] = {
    "jackson_pollock_3": _jackson_pollock_3,
    "jackson_pollock_7": _jackson_pollock_7,
    "durnin_womersley_4": _durnin_womersley_4,
    "petroski_1995_male_4": _petroski_1995_male_4,
    "petroski_1995_female_4": _petroski_1995_female_4,
    "guedes_1985_3": _guedes_1985_3,
    "ymca_4": _ymca_4,
    "ymca_3": _ymca_3,
    "weltman_1988_female": _weltman_1988_female,
    "slaughter_2sites_simple": _slaughter_2sites_simple,
    "faulkner_1968_4": _faulkner_1968_4,
}


def _durnin_coefficients(sex: str, age_years: int) -> tuple[float, float]:
    if age_years < 17:
        return (1.1533, 0.0643) if sex == "male" else (1.1369, 0.0598)
    if age_years <= 19:
        return (1.1620, 0.0630) if sex == "male" else (1.1549, 0.0678)
    if age_years <= 29:
        return (1.1631, 0.0632) if sex == "male" else (1.1599, 0.0717)
    if age_years <= 39:
        return (1.1422, 0.0544) if sex == "male" else (1.1423, 0.0632)
    if age_years <= 49:
        return (1.1620, 0.0700) if sex == "male" else (1.1333, 0.0612)
    return (1.1715, 0.0779) if sex == "male" else (1.1339, 0.0645)


def _sum_fields(values: Any, fields: tuple[str, ...]) -> float | None:
    total = 0.0
    for field in fields:
        value = _read_float(values, field)
        if value is None:
            return None
        total += value
    return total


def _siri(density: float | None) -> float | None:
    if density is None or density <= 0:
        return None
    return 495 / density - 450


def _estimated_range(value: float | None, confidence: str | None) -> tuple[float | None, float | None]:
    if value is None or confidence is None:
        return None, None
    margin = 3.0 if confidence == "medium" else 4.0
    return _round_percent(max(0, value - margin)), _round_percent(min(75, value + margin))


def _field_label(field: str) -> str:
    return {
        "skinfold_chest_mm": "dobra peitoral",
        "skinfold_midaxillary_mm": "dobra axilar media",
        "skinfold_subscapular_mm": "dobra subescapular",
        "skinfold_triceps_mm": "dobra tricipital",
        "skinfold_biceps_mm": "dobra bicipital",
        "skinfold_abdominal_mm": "dobra abdominal",
        "skinfold_suprailiac_mm": "dobra suprailiaca",
        "skinfold_thigh_mm": "dobra coxa",
        "skinfold_calf_mm": "dobra panturrilha",
        "abdomen_cm": "abdomen",
        "height_cm": "altura",
        "hip_cm": "quadril",
        "waist_cm": "cintura",
        "weight_kg": "peso",
    }.get(field, field)


def _is_plausible_field_value(field: str, value: float) -> bool:
    ranges = {
        "height_cm": (90.0, 250.0),
        "weight_kg": (20.0, 300.0),
        "abdomen_cm": (30.0, 250.0),
        "waist_cm": (30.0, 250.0),
        "hip_cm": (35.0, 260.0),
    }
    minimum, maximum = ranges.get(field, (2.0, 120.0))
    return minimum <= value <= maximum


def _read(values: Any, key: str) -> Any:
    if values is None:
        return None
    if isinstance(values, dict):
        return values.get(key)
    return getattr(values, key, None)


def _read_float(values: Any, key: str) -> float | None:
    value = _read(values, key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_int(values: Any, key: str) -> int | None:
    value = _read_float(values, key)
    return int(value) if value is not None else None


def _round_percent(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None
