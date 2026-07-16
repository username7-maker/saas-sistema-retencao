# ACTUAR-SPIKE - Spec 057

## Status

Preflight executed in Phase 11.1 on 2026-07-16.

Live Actuar execution was attempted after explicit operator authorization for the designated test student `Erick Bedin`.

The corrected credentials passed login and reached `#/inicio`.

The attempt did not open or save an assessment because the Actuar search returned two candidates named `Erick Bedin`. The spike stopped before selecting a candidate to avoid writing an assessment to the wrong person.

This is a controlled NO-GO for implementation, not a failure of the local anthropometric V1.

## Inputs checked

- No real `.env` was present in this worktree; only `.env.example` files exist.
- Credentials were injected only into the transient shell process for the authorized test. They were not written to repository files.
- Redacted local screenshot evidence was produced under `.planning/phases/11.1-anthropometry-actuar-core/evidence/` and is intentionally not required for source control.
- Corrected credentials were validated live, but the test student requires disambiguation before any write.
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
| Test student uniquely identified | FAIL | API search returned two candidates named `Erick Bedin`: one with birthdate `2005-04-27`, one with birthdate `2004-04-27`. |
| Required fields identified | PARTIAL | Static/historical evidence identifies fields used by the existing bioimpedance flow, but live requiredness for anthropometry was not verified because no candidate was selected. |
| Muscle mass can be empty | BLOCKED | The spike stopped before opening the assessment form due ambiguous test student selection. Existing successful payloads filled `muscle_mass_kg`, while Spec 056 intentionally keeps muscle mass unavailable. |
| Date, weight, height and body fat can save | BLOCKED | The minimum anthropometry payload was not tested because selecting either candidate without operator disambiguation would risk writing to the wrong Actuar record. |
| Actuar differentiates assessment types | PARTIAL | Existing flow opens `Nova avaliacao` and `Composicao corporal e perimetria`; no separate anthropometry/bioimpedance distinction was verified live. |
| `external_assessment_id` capture method confirmed | FAIL/PARTIAL | Historical saved URLs expose an assessment-route id, and the extension can log an assessment id, but the backend currently persists/returns the Actuar person id as `actuar_external_id`. This does not satisfy the V1.1 contract. |
| History/report appearance confirmed | BLOCKED | Requires disambiguated test student and live save. |
| Duplicate detection confirmed | BLOCKED | Requires disambiguated test student and save/reopen behavior. |
| Save/update/close behavior confirmed | BLOCKED | Requires disambiguated test student before opening and saving the form. |
| Timeout-after-click behavior confirmed | BLOCKED | Requires controlled live timeout test after candidate disambiguation. |

## Decision

NO-GO for Actuar Core implementation.

Do not implement `assessment_push`, anthropometric Actuar jobs, bridge payloads, retries, or automatic sync until:

1. an operator disambiguates which `Erick Bedin` candidate is the test record;
2. corrected Actuar credentials or an already-authenticated Actuar browser session remain available;
3. a live save proves muscle mass can remain empty;
4. date, weight, height and official body fat can save without dobras/perimetros;
5. the created external assessment id is captured and persisted as an assessment id, not only as a person id;
6. duplicate-detection behavior is proven after save/reopen/timeout.

Until then, the product state remains:

```text
Envio ao Actuar ainda nao disponivel para antropometria.
```
