# ACTUAR-SPIKE - Spec 057

## Status

Preflight executed in Phase 11.1 on 2026-07-16.

Live Actuar execution was attempted after explicit operator authorization for the designated test student `Erick Bedin`.

The corrected credentials passed login and reached `#/inicio`.

The Actuar search returned two candidates named `Erick Bedin`; the active record was identified through Actuar OData status:

- `2005-04-27`, `IdAtendimento=CA8400`, `Situacao=I`;
- `2004-04-27`, `IdAtendimento=LR3583`, `Situacao=A`.

A controlled save was executed only against the active record `LR3583`.

The save succeeded with the minimal anthropometry payload we control (`weight`, `height_cm`, `body_fat_percent`) and without sending `muscle_mass_kg`. However, Actuar persisted `CurrentMuscleMass=0` and `CalculateMuscleMass=true`. This is not acceptable as an automatic sync result for V1.1 because zero would be presented as a real muscle-mass value.

This is a controlled NO-GO for implementation, not a failure of the local anthropometric V1.

## Inputs checked

- No real `.env` was present in this worktree; only `.env.example` files exist.
- Credentials were injected only into the transient shell process for the authorized test. They were not written to repository files.
- Redacted local screenshot evidence was produced under `.planning/phases/11.1-anthropometry-actuar-core/evidence/` and is intentionally not required for source control.
- Corrected credentials were validated live.
- The active test student was identified via `Situacao=A`.
- A controlled save was executed against the active test student.
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
| Login with authorized spike credentials | PASS | Actuar reached `#/inicio` with corrected credentials. |
| Test student uniquely identified | PASS | `PessoasAgrupamentos` returned `Situacao=I` for the 2005-04-27 record and `Situacao=A` for the 2004-04-27 / `LR3583` record. |
| Required fields identified | PARTIAL | Live form exposes editable `weight`, `height_cm`, `body_fat_percent` and `muscle_mass_kg`; no separate date input was visible on the body-composition tab. |
| Muscle mass can be empty | FAIL | We did not send `muscle_mass_kg`, but Actuar saved `CurrentMuscleMass=0` with `CalculateMuscleMass=true`. This would create a misleading zero value. |
| Date, weight, height and body fat can save | PASS/PARTIAL | Save confirmed with `weight=80`, `height_cm=180`, `body_fat_percent=18.5`; date appears controlled by the Actuar assessment record rather than a visible body-composition input. |
| Actuar differentiates assessment types | PARTIAL | Existing flow opens `Nova avaliacao` and `Composicao corporal e perimetria`; no separate anthropometry/bioimpedance distinction was verified live. |
| `external_assessment_id` capture method confirmed | PASS/PARTIAL | Post-save route exposed an assessment-id candidate and the read-only history returned `AssessmentId` hash `c9b9ba001d73`; backend contract still needs to persist this as the assessment id, not the person id. |
| History/report appearance confirmed | PARTIAL | `GetAssessmentsByPersonId` returned the saved July 2026 body-composition record with the same assessment-id hash. Full report appearance was not validated. |
| Duplicate detection confirmed | BLOCKED | Requires save/reopen/timeout behavior and a local outbox/idempotency contract before automatic retry. |
| Save/update/close behavior confirmed | PASS | Actuar showed `Alterações salvas com sucesso` and route changed to an edit route containing person id plus assessment id. |
| Timeout-after-click behavior confirmed | BLOCKED | Requires a controlled timeout test; no retry policy may be implemented from this spike alone. |

## Decision

NO-GO for Actuar Core implementation.

Do not implement `assessment_push`, anthropometric Actuar jobs, bridge payloads, retries, or automatic sync until:

1. product/engineering decides how to prevent or handle Actuar's `CurrentMuscleMass=0` result for anthropometry;
2. a follow-up spike proves a safe way to keep muscle mass unavailable in Actuar, or the integration is explicitly limited with a visible warning/manual-review state;
3. the created external assessment id is captured and persisted as an assessment id, not only as a person id;
4. duplicate-detection behavior is proven after save/reopen/timeout.

Until then, the product state remains:

```text
Envio ao Actuar ainda nao disponivel para antropometria.
```
