# ACTUAR-SPIKE - Spec 057

## Status

Preflight executed in Phase 11.1 on 2026-07-16.

Live Actuar execution was not performed because this workspace does not contain explicit Actuar credentials, a designated test student, or an operator-approved browser session for this new anthropometry spike.

This is a controlled NO-GO for implementation, not a failure of the local anthropometric V1.

## Inputs checked

- No `ACTUAR_*` environment variables were present in the current shell.
- No real `.env` was present in this worktree; only `.env.example` files exist.
- Existing Actuar/bridge tests are green:

```text
py -3.12 -m pytest tests\test_actuar_settings_service.py tests\test_actuar_settings_router.py tests\test_actuar_bridge_service.py tests\test_actuar_bridge_router.py tests\test_body_composition_sync.py tests\test_actuar_browser_client.py
69 passed
```

- Historical project notes show the validated bioimpedance Actuar flow used `weight`, `height_cm`, `body_fat_percent`, `muscle_mass_kg` and `total_energy_kcal`.
- The current backend/extension field maps still include `muscle_mass_kg` and `total_energy_kcal`.
- The current server-side provider returns the resolved Actuar person/member id as `actuar_external_id`; the extension action log can capture a created assessment id, but that id is not currently the persisted external assessment id contract.

## Matrix

| Check | Status | Evidence |
| --- | --- | --- |
| Required fields identified | PARTIAL | Static/historical evidence identifies fields used by the existing bioimpedance flow, but live requiredness for anthropometry was not verified. |
| Muscle mass can be empty | BLOCKED | No live Actuar test was executed. Existing successful payloads filled `muscle_mass_kg`, while Spec 056 intentionally keeps muscle mass unavailable. |
| Date, weight, height and body fat can save | BLOCKED | This is the minimum anthropometry payload, but it requires a live Actuar save test with a designated test student. |
| Actuar differentiates assessment types | PARTIAL | Existing flow opens `Nova avaliacao` and `Composicao corporal e perimetria`; no separate anthropometry/bioimpedance distinction was verified live. |
| `external_assessment_id` capture method confirmed | FAIL/PARTIAL | Historical saved URLs expose an assessment-route id, and the extension can log an assessment id, but the backend currently persists/returns the Actuar person id as `actuar_external_id`. This does not satisfy the V1.1 contract. |
| History/report appearance confirmed | BLOCKED | Requires live Actuar save and reopening the student's Actuar history/report. |
| Duplicate detection confirmed | BLOCKED | Requires live search/reopen behavior after a save. |
| Save/update/close behavior confirmed | BLOCKED | Requires live Actuar interaction. |
| Timeout-after-click behavior confirmed | BLOCKED | Requires controlled live timeout test and evidence. |

## Decision

NO-GO for Actuar Core implementation.

Do not implement `assessment_push`, anthropometric Actuar jobs, bridge payloads, retries, or automatic sync until:

1. an operator provides a designated test student;
2. Actuar credentials/session are explicitly approved for this spike;
3. a live save proves muscle mass can remain empty;
4. date, weight, height and official body fat can save without dobras/perimetros;
5. the created external assessment id is captured and persisted as an assessment id, not only as a person id;
6. duplicate-detection behavior is proven after save/reopen/timeout.

Until then, the product state remains:

```text
Envio ao Actuar ainda nao disponivel para antropometria.
```
