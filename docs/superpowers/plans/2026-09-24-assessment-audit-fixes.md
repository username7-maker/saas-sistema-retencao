# Assessment Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five confirmed assessment audit findings without changing existing report layout or assessment APIs.

**Architecture:** Keep method/date/score rules in backend report and assessment services. Make the manual assessment form track the exact payload used for its preview. Preserve old records and pending worktree changes.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, React, TypeScript, Vitest, Playwright.

**Spec:** `specs/050-anthropometry-protocols-body-map/spec.md`, `specs/054-anthropometry-lee-muscle-mass/spec.md`, `.planning/phases/09.23-anthropometry-lifecycle-guided-camera/UI-SPEC.md`.

## Global Constraints

- Preserve current scanner, OCR, review, delivery, HTML/PDF layout, tenant isolation and API routes.
- Do not migrate or rewrite historical evaluations.
- Keep unknown legacy methods non-comparable rather than assuming a protocol.
- Publish the validated backend and frontend to the existing pilot via CLI, without GitHub, under the user's standing rollout preference.

## Review Focus

- Two manual fat protocols must not share a comparison signature.
- A changed input or an old in-flight response must invalidate the preview used for confirmation.
- A historical assessment's age must be calculated at its local assessment date.
- Score comparison must consider every actual waist component.
- Future or naive dates and late-evening São Paulo dates must follow one consistent time policy.

---

### Task 1: Protocol-aware comparison

**Files:** `saas-backend/app/services/assessment_anthropometry_report_service.py`, `saas-backend/tests/test_body_composition_report_v2.py`.

- [x] Add a failing regression with two different supported protocols and one same-protocol control.
- [x] Run it red, then derive method signature from saved protocol and formula version; leave legacy unknown non-comparable.
- [x] Run focused report tests green.

### Task 2: Stable manual preview and historical age

**Files:** `saas-frontend/src/components/assessments/AssessmentRegistrationComposer.tsx`, `saas-frontend/src/test/AssessmentRegistrationComposer.test.tsx`.

- [x] Add failing tests for changed fields after preview, stale responses, and historical birthday boundary.
- [x] Run them red, then tie confirmation to an unchanged preview payload and derive default age from assessment date.
- [x] Run focused UI tests green.

### Task 3: Score component compatibility

**Files:** `saas-backend/app/services/body_composition_report_domain.py`, `saas-backend/tests/test_body_composition_report_v2.py`.

- [x] Add a failing test where waist/height availability changes but waist/hip stays constant.
- [x] Run it red, then require the same subcomponents and per-metric comparability.
- [x] Run focused report tests green.

### Task 4: Manual assessment dates

**Files:** `saas-backend/app/services/assessment_anthropometry_service.py`, `saas-backend/app/services/assessment_anthropometry_report_service.py`, `saas-backend/tests/test_anthropometry_lifecycle.py`, `saas-backend/tests/test_body_composition_report_v2.py`.

- [x] Add failing future-date and São Paulo midnight-boundary tests.
- [x] Run them red, then normalize naive input as São Paulo, store UTC, reject future input and use local report date.
- [x] Run focused tests green.

### Task 5: Final verification

- [x] Run backend and frontend complete suites, lint, production build and existing scanner/assessment browser E2E.
- [x] Inspect git diff for unrelated changes and report results plus any remaining physical-device validation gap.
- [x] Deploy backend, then frontend to the pilot by CLI and verify health, version and assessment route.

## Execution evidence — 2026-09-24

- Backend red tests reproduced protocol mismatch, score component drift, future date acceptance and UTC calendar drift; frontend red tests reproduced historical-age and stale-preview failures.
- Final checks: 1,384 backend tests passed (3 skipped); 305 frontend tests passed; ESLint, frontend production build/bundle budget, critical Ruff checks and 3 Playwright browser tests passed.
- Synthetic anthropometry PDF with different fat protocols had no fat delta, retained skinfold/perimetry sections and had four nonblank pages.
- CLI rollout without GitHub: Railway API deployment `846cf9e3-9600-4856-9ce7-a6ad37bc5866` and worker deployment `fd9f7788-468b-4b6d-b3b6-c97312cb5a06` reached SUCCESS; Vercel deployment `dpl_pkk9aaoczqyjBB8dzoqUuppRdBJm` reached READY and was aliased to the pilot. API `/health/ready` and pilot assessment route returned HTTP 200; the deployed assessment bundle contains the new preview guard.
- Physical Android/iPhone validation remains pending. No production member assessment was created or modified in verification.

## Follow-up — formula variants

- A second audit found that the same Slaughter protocol can use different ethnicity/maturity choices, and Durnin uses different coefficients across age bands. The prior comparison signature omitted both, so an incompatible fat change could appear as a physiological delta.
- The report now includes persisted sex, protocol-required choices and the actual Durnin coefficients in the comparison signature. Missing required evidence disables comparison conservatively. The report still uses the same layout and does not rewrite saved assessments.
- Regression tests cover changed and unchanged choices, missing choices, changed and unchanged Durnin age bands, derived fat mass and score. Focused suite: 46 passed; complete backend suite: 1,384 passed and 3 skipped.
- CLI rollout of API and worker used `railway up ./saas-backend --path-as-root` from the repository root, retaining the Dockerfile and Railway configuration. API deployment `56455b2b-30f1-4b38-9436-82ce45a5d665` and worker deployment `8543612a-8d91-4903-a58b-16166641aa6c` reached SUCCESS. API `/health/ready` returned HTTP 200, and worker logs confirmed scheduler startup. No GitHub push or frontend redeploy was needed.
