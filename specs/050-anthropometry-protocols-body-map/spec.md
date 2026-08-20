# Spec 050 - Anthropometry Protocols + Body Map

Status: Approved
Date: 2026-07-07
Owner: Cordex
Implementation target: Cordex Gym OS / Avaliacoes / Bioimpedancia v2

## Context

The current Body Composition by Measurements V1 correctly separates the official body fat value from the raw bioimpedance value. The next product correction is presentation and protocol coverage: manual measurements should not appear only as a loose table, and the assessment screen needs a protocol selector comparable to the operational list used by gyms.

This feature must keep the current Bioimpedancia v2 workflow. It must not create a parallel physical assessment module, must not copy Actuar proprietary UI/code, and must only calculate protocols where a public formula is available and implemented defensibly.

## Functional Requirements

FR-1. The report MUST display manual perimetry with a neutral body map plus the existing measurement table.

FR-2. The report MUST keep the measurement table with current, previous and delta values.

FR-3. The assessment form MUST expose a protocol selector containing the operational protocol names requested by the user.

FR-4. The system MUST distinguish protocols that are calculated automatically from protocols that are catalog/manual-review only in V1.

FR-5. The backend MUST persist skinfold measurements needed by supported skinfold protocols.

FR-6. The backend MUST calculate body fat for supported public skinfold protocols when required fields are present.

FR-7. The backend MUST NOT calculate unsupported protocols by guessing formulas.

FR-8. The official value for report, IA, PDF, WhatsApp and Kommo MUST remain `body_fat_used_percent`.

FR-9. `body_fat_percent` MUST remain only raw/legacy bioimpedance compatibility.

FR-10. Perimetry fields such as arms, thighs, calves, chest and shoulders MUST remain evolution/context fields and MUST NOT be used directly in circumference fat formulas.

## Non-Functional Requirements

NFR-1. No backend route or frontend route may be removed.

NFR-2. Existing OCR, Actuar sync, WhatsApp, Kommo and PDF flows must remain compatible.

NFR-3. Protocol calculations must return quality flags when data is missing, age/sex does not match, or protocol is catalog-only.

NFR-4. UI labels must use estimate language and must not imply clinical diagnosis.

## Acceptance Criteria

AC-1. Given a report with manual measures, when the report page opens, then a "Mapa corporal de medidas" is shown together with the measurement table. Covers FR-1 and FR-2.

AC-2. Given the Bioimpedancia v2 form, when the teacher opens measurements, then a protocol dropdown includes the requested protocol catalog. Covers FR-3.

AC-3. Given a supported Jackson/Pollock 3-site male protocol with required skinfolds, when the evaluation is saved, then `body_fat_used_percent` is calculated from the supported protocol and `body_fat_method` is `skinfold_protocol`. Covers FR-5, FR-6 and FR-8.

AC-4. Given an unsupported/manual-only protocol, when it is selected without manual override, then the system does not invent body fat and adds a quality flag. Covers FR-4 and FR-7.

AC-5. Given a report context, when body fat is displayed, then the official value comes from `body_fat_used_percent` and raw bioimpedance is explicitly labeled. Covers FR-8 and FR-9.

AC-6. Given circumference fields and evolution fields, when the backend calculates Navy/RFM/GeneOS, then only neck, waist/abdomen, hip, height, weight and sex participate in the calculation. Covers FR-10.

## Edge Cases

EC-1. Missing required skinfold fields returns incomplete quality flags and falls back to available official source.

EC-2. Age outside the protocol age range returns a warning flag but does not block saving.

EC-3. Sex mismatch returns a warning flag and prevents automatic calculation for that protocol.

EC-4. Impossible skinfold values return `impossible_measurement_value`.

EC-5. Unsupported protocol keys are preserved for notes/manual work but do not calculate.

## API Contracts

BodyCompositionEvaluationCreate/Update extends current contract with optional skinfold fields:

```ts
interface BodyCompositionSkinfoldFields {
  skinfold_chest_mm?: number | null;
  skinfold_midaxillary_mm?: number | null;
  skinfold_subscapular_mm?: number | null;
  skinfold_triceps_mm?: number | null;
  skinfold_biceps_mm?: number | null;
  skinfold_abdominal_mm?: number | null;
  skinfold_suprailiac_mm?: number | null;
  skinfold_thigh_mm?: number | null;
  skinfold_calf_mm?: number | null;
  measurement_protocol?: string | null;
}
```

`body_fat_method` adds:

```ts
type BodyFatMethod = "legacy_bioimpedance" | "navy_circumference" | "rfm" | "geneos_composite" | "manual_override" | "skinfold_protocol";
```

## Data Models

| Field | Type | Notes |
| --- | --- | --- |
| measurement_protocol | string(80) | protocol key/catalog selector |
| skinfold_*_mm | numeric(6,2) | optional skinfold thickness values |
| body_fat_used_percent | numeric | official percent used by product |
| body_fat_method | string | includes `skinfold_protocol` |
| data_quality_flags_json | jsonb | includes protocol flags |

## Out of Scope

OS-1. Do not copy Actuar layout, code or proprietary formulas.

OS-2. Do not create a separate physical assessment module.

OS-3. Do not recalculate old evaluations without manual measures.

OS-4. Do not send new perimetry/skinfold fields to Actuar in V1.

OS-5. Do not use arms, thighs, calves, chest or shoulders directly in circumference body fat formulas.

OS-6. Do not replace bioimpedance muscle mass with anthropometric estimates.

OS-7. Do not present body fat as a clinical diagnosis.
