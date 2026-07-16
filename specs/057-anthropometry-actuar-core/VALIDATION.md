# Validation - Spec 057

## Scope

This validation covers the Phase 11.1 preflight and the authorized live login attempt. It does not claim a live Actuar save.

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
student lookup result: FAIL - ambiguous
candidate 1 birthdate: 2005-04-27
candidate 2 birthdate: 2004-04-27
save attempted: no
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

## Result

NO-GO for implementation.

The spike cannot advance to Actuar Core until a live, operator-approved Actuar test proves:

- the designated `Erick Bedin` candidate is disambiguated by birthdate, email or external id;
- muscle mass can be empty;
- date, weight, height and official body fat are sufficient;
- the created external assessment id can be captured and persisted;
- duplicate handling is safe after save/reopen/timeout.
