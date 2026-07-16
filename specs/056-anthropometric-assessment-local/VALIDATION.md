# Validation - Spec 056

## Local evidence

Backend focused:

```text
py -3.12 -m pytest tests\test_assessment_anthropometry_service.py tests\test_assessment_anthropometry_report.py
9 passed
```

Backend history/regression focused:

```text
py -3.12 -m pytest tests\test_assessment_anthropometry_service.py tests\test_assessment_anthropometry_report.py tests\test_assessment_service.py
24 passed
```

Backend bioimpedance characterization bundle:

```text
py -3.12 -m pytest tests\test_assessment_anthropometry_service.py tests\test_assessment_anthropometry_report.py tests\test_assessment_service.py tests\test_body_composition.py tests\test_body_composition_anthropometry_service.py tests\test_body_composition_sync.py
77 passed
```

Frontend focused:

```text
npm.cmd test -- AnthropometricAssessmentForm.test.tsx NewAssessmentPage.test.tsx MemberProfile360Page.test.tsx MemberBodyCompositionTab.test.tsx bodyCompositionAnthropometryPreview.test.ts
21 passed
```

Frontend build:

```text
npm.cmd run build
PASS
```

Frontend lint:

```text
npm.cmd run lint
PASS with 2 pre-existing warnings in src/pages/method/MethodOsPage.tsx
```

Alembic:

```text
py -3.12 -m alembic heads
20260716_0051 (head)
```

PostgreSQL migration smoke:

```text
docker run -d --name phase11_anthro_db -e POSTGRES_DB=aigymos -e POSTGRES_USER=aigymos -e POSTGRES_PASSWORD=aigymos_dev -p 55432:5432 postgres:16-alpine
DATABASE_URL=postgresql+psycopg2://aigymos:aigymos_dev@localhost:55432/aigymos CPF_ENCRYPTION_KEY=<local-test-key> py -3.12 -m alembic upgrade head
DATABASE_URL=postgresql+psycopg2://aigymos:aigymos_dev@localhost:55432/aigymos CPF_ENCRYPTION_KEY=<local-test-key> py -3.12 -m alembic current
20260716_0051 (head)
```

Schema spot-check:

```text
alembic_version: 20260716_0051
assessments: assessment_method, record_origin, anthropometry_snapshot_json, idempotency_key, calculation_hash
members: height_cm, sex_for_clinical_calculation
constraint: uq_assessments_gym_idempotency_key
```

API smoke against migrated PostgreSQL:

```text
register/login: PASS
member create: PASS
GET /api/v1/assessments/anthropometry/protocols: PASS
POST /api/v1/assessments/members/{member_id}/anthropometry/preview: PASS body_fat_pct=12.49
POST /api/v1/assessments/members/{member_id}/anthropometry: PASS
idempotent repeat with same Idempotency-Key: PASS same assessment_id
GET /api/v1/assessments/members/{member_id}: PASS history_badge=Antropometria
GET /api/v1/assessments/members/{member_id}/{assessment_id}/pdf: PASS PDF bytes returned with X-Report-Scope=anthropometry
DB tasks: PASS offsets=[8,14,75,90]
snapshot_schema: anthropometry_snapshot_v1
calculation_hash_len: 64
```

FastAPI import:

```text
py -3.12 -c "from app.main import app; print('fastapi import ok', len(app.routes))"
fastapi import ok 304
```

Spec Kit:

```text
specify check
Specify CLI is ready to use
```

GSD health:

```text
gsd-sdk.cmd query validate.health
status: degraded
```

The degraded state is the existing baseline of historical `W007` phase-directory warnings and `I001` missing summary notices. Phase 11 did not introduce a new health warning in the command output.

Diff hygiene:

```text
git diff --check
PASS
```

## Pilot deployment - 2026-07-16

Production/pilot database migration:

```text
railway run ... alembic current
20260715_0052

railway run ... alembic upgrade head
Running upgrade 20260715_0052 -> 20260716_0050, assessment anthropometry local
Running upgrade 20260716_0050 -> 20260716_0051, assessment origin backfill

railway run ... alembic current
20260716_0051 (head)
```

The pilot database already contained the abandoned `20260715_0052` revision from the superseded unified-assessment branch. Spec 056 added a no-op Alembic marker for that revision and chained the local V1 migrations after it. No Actuar Core code or old unified-assessment implementation was merged into Spec 056.

Deployments:

```text
Railway api:    388a36be-0938-44b6-80b0-1605c2986cb6 - SUCCESS
Railway worker: b7dc8573-1096-43c2-89f9-b2c79146e713 - SUCCESS
Vercel:         dpl_yvFpA7SDmYhFVpxH5ccE8YaGx8Hw - Ready
Frontend alias: https://saas-frontend-pearl.vercel.app
Backend URL:    https://ai-gym-os-api-production.up.railway.app
```

Published smoke checks:

```text
GET /health       -> ok
GET /health/ready -> ok
GET frontend alias -> 200, SPA root present
```

## Notes

- `npm.cmd ci` was required because the isolated worktree did not have `node_modules`.
- `npm.cmd ci` reported 12 existing dependency audit findings from the lockfile. They were not changed because dependency remediation is outside Spec 056.
- The bioimpedance tab/component was covered by characterization tests and not edited.
- `npm.cmd run build` reported the existing Browserslist/caniuse-lite freshness notice. It did not fail the build.
- The existing Playwright E2E `tests/e2e/body-composition-anthropometry.spec.ts` was attempted as a non-gating characterization of the legacy report surface and failed on stale expected copy (`Fonte oficial da gordura corporal`). The page rendered the current documentary report layout; no file in that legacy report/E2E path was changed by Spec 056.
