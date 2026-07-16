# Validation - Spec 057

## Scope

This validation covers the Phase 11.1 preflight, authorized live login, active-candidate disambiguation and one controlled Actuar save against the active test record.

## Commands

```text
py -3.12 -m pytest tests\test_actuar_settings_service.py tests\test_actuar_settings_router.py tests\test_actuar_bridge_service.py tests\test_actuar_bridge_router.py tests\test_body_composition_sync.py tests\test_actuar_browser_client.py
69 passed
```

## Environment check

```text
real .env in worktree: none
credentials persisted in repository files: no
```

Only `.env.example` files were present. Authorized credentials were injected only into the transient shell process for the spike.

## Live login attempt

```text
student: Erick Bedin
base URL: https://app.actuar.com
login result: PASS
Actuar route after login: #/inicio
student lookup result: PASS via Actuar status
inactive candidate: 2005-04-27 / Situacao=I / IdAtendimento=CA8400
active candidate: 2004-04-27 / Situacao=A / IdAtendimento=LR3583
save attempted: yes, active candidate only
save result: PASS
assessment id captured: yes, redacted hash c9b9ba001d73
muscle mass sent by Cordex: no
muscle mass persisted by Actuar: CurrentMuscleMass=0
```

Redacted local screenshot evidence was created under:

```text
.planning/phases/11.1-anthropometry-actuar-core/evidence/
```

## Static findings

- Existing body-composition Actuar flow maps `weight`, `height_cm`, `body_fat_percent`, `muscle_mass_kg` and `total_energy_kcal`.
- Historical GSD notes show prior successful bioimpedance Actuar smoke filled muscle mass and total energy.
- The current server-side provider returns the resolved Actuar person/member id as `actuar_external_id`.
- The extension can log a created assessment id after save, but this is not yet the persisted external assessment id contract required by Spec 057.
- The controlled anthropometry save proved that Actuar can save without Cordex sending `muscle_mass_kg`, but Actuar persisted `CurrentMuscleMass=0`; therefore the "muscle mass can be empty" requirement failed.

## Result

NO-GO for implementation.

The spike cannot advance to Actuar Core until a live, operator-approved Actuar test proves:

- a safe treatment for Actuar's `CurrentMuscleMass=0` behavior;
- the created external assessment id can be captured and persisted by the backend as an assessment id;
- duplicate handling is safe after save/reopen/timeout.
