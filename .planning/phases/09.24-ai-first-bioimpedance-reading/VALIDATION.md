# Validation - Phase 09.24

## Local validation

- Backend focused safety suite: 26 passed.
- Frontend focused OCR/workspace suite: 34 passed.
- Frontend ESLint: passed with zero errors.
- Frontend production build (`tsc -b && vite build`): passed.
- Backend full suite: 1,246 passed and one unrelated baseline assertion failed in
  `test_body_composition_ai_service.py` (legacy fallback risk-flag wording).
- Frontend full suite: 210 passed and seven unrelated baseline page expectation
  tests failed; the external audit spec also requires `AUDIT_FRONTEND_URL` and
  `AUDIT_BACKEND_URL`.
- New backend parser and tests pass Ruff. Existing repository-wide line-length
  debt remains outside this hotfix.

## Safety checks

- Assisted read calls the backend before starting local OCR.
- Local OCR is used only after a transient/provider failure and is sent back to
  the backend for canonical demographic and BMI validation.
- Authentication, invalid-file and cancelled requests do not trigger local OCR.
- Chronological age is derived from birthdate at the selected assessment date.
- Physical age never becomes chronological age.
- Member sex and valid member height remain authoritative; photo divergence is
  explicit and blocking only when clinically relevant.
- Missing photo evidence is discarded. Missing demographic evidence does not
  block a valid authoritative profile value.
- BMI uses `max(0.5, 2%)` tolerance; a previous-weight variation above 20% is a
  warning and does not replace the new weight.
- Switching files clears the previous transient result and blocks saving until
  the newly selected image is read or removed.
- No image, receipt text or member PII is written to application logs.
- No migration or historical-data update is part of this release.

## Pilot rollout

- Production source commit: `b272f5cf2f61e07e32ba89ca8483b067601e155c`.
- Railway API deployment: `098cf6fe-93f6-45db-aa26-d55e2d9faf13` (`SUCCESS`).
- Railway worker deployment: `880c371f-5c10-46f3-be20-6b4a6ccb58b7` (`SUCCESS`).
- Vercel deployment: `dpl_8qAt9AASwyKKu3edfmf7q4bqq2Sg` (`READY`).
- Pilot alias: `https://saas-frontend-pearl.vercel.app`.
- API `/health/ready`: HTTP 200 with the expected release SHA.
- Frontend root and assessment report route: HTTP 200; the production bundle
  contains the same release SHA.
- Anonymous `parse-image` request: HTTP 401, confirming the protected boundary.
- Worker startup log reports the same release SHA and the scheduler started.
- `BODY_COMPOSITION_IMAGE_AI_VALIDATION_ENABLED=true` is active for API and
  worker in the pilot environment.
- No database migration ran and no client evaluation was created, edited,
  deleted or recalculated during rollout/smoke.
- Authenticated smoke with real webcam photos remains an operational check in
  the logged-in pilot session because this workstation has no reusable test
  session or anonymized receipt fixture.

## Tezewa receipt remediation - 2026-09-03

- Backend parser regression suite: 30 passed; Ruff passed for changed backend
  source files.
- Frontend OCR/workspace regression subset: 21 passed; ESLint completed with no
  errors (two pre-existing Method OS hook warnings); production build passed.
- A user-provided Tezewa receipt was processed transiently with production AI
  configuration. The image, receipt identifier and raw text were not copied to
  fixtures, logs or persistent storage.
- The real receipt check accepted 26 structured values after adding support for
  narrow-paper line wrapping, `Woman`, `Fat free`, `Body moisture`, `Basal
  metabolism` and unitless device labels.
- The receipt still required one intentional confirmation: printed/read values
  of 65.1 kg, 158 cm and BMI 23.1 are mathematically inconsistent. The system
  did not fabricate a replacement and reduced the UI to one friendly review
  instruction.
- Vision detail is high. The dedicated request timeout is 45 seconds with no
  hidden SDK retries; a successful real-image read completed in under 30
  seconds during validation.
- Technical warning lists, raw OCR text, provider errors and timing details are
  no longer shown in the professor workflow.
- Remediation source commit: `6302cd93c907d96e9581d2f8b9ecd16fcb857d55`.
- Railway API deployment: `b1025208-fa09-4856-81da-545fa97fbed8` (`SUCCESS`).
- Railway worker deployment: `9080bf2b-b672-4a40-9452-8902051ec78b` (`SUCCESS`).
- Vercel deployment: `dpl_5qSXUUBe3SkQisfMmdw2Xed3hkV3` (`READY`).
- Pilot alias, frontend bundle, API health response and worker startup all
  expose the same remediation source SHA.
- No database migration or client-data mutation was performed.

## Field-by-field reading hardening - 2026-09-23

- Range separators damaged as `°`/`º` are rejected when their endpoints are
  presented as the principal value without a separate measured number.
- Current weight no longer accepts target, control or fat-free weight labels.
- Printed date mismatches require explicit review; timestamp evidence must
  contain the actual date and minute. BMI, fat-mass percentage and fat-free
  mass consistency are checked without inventing replacement values.
- An accepted printed timestamp is saved only when its Sao Paulo calendar date
  matches the selected evaluation date; reading a new receipt clears any stale
  timestamp from the previous image. The accepted time is visible in the UI.
- Recovery reads include waist-hip ratio, inorganic salt, muscle mass and BMR;
  missing salt or BMR triggers the assisted-read fallback from local OCR.
- A new image replaces receipt measurements while preserving anthropometry,
  member profile fields and manual override inputs.
- Five new backend regressions were observed failing before the fix and passing
  after it. Related backend suite: 105 passed. Frontend suite: 301 passed.
  ESLint, production build and bundle budget passed.
- Direct CLI rollout without GitHub: Railway API
  `f3b7644b-6e03-4ef1-b686-8ed5d19cc1cc` and worker
  `38a6d0a5-13d9-434e-97c7-1c6c84798b8e` succeeded; Vercel deployment
  `dpl_95RKN4UonNCekog6yUenGpYFwswY` is READY and aliased to
  `https://saas-frontend-pearl.vercel.app`.
- Public API readiness returned `ok`, and the pilot frontend served the new
  bundle with HTTP 200. Real-device camera validation remains to be performed
  by staff with Android/iPhone access.

## Full verification follow-up - 2026-09-23

- Reviewed the image endpoint, assisted-read normalization, field evidence,
  recovery pass, local OCR, form population, date handling and save boundary.
- Added regression tests for sex evidence (`Female` must not prove `male`),
  nonnumeric disagreements between primary and recovery reads, replacement of
  values with invalid primary evidence, preservation of conflict state,
  printed timestamp/date disagreement and equivalent UTC/local timestamps.
- Verified that a thermal receipt can join a label and its measured number
  (`Basal metabolism1366`); the evidence parser now accepts that measured value
  while still rejecting range-only endpoints.
- A printed timestamp now participates in the date conflict check even when
  the AI omits a separate evaluation date. A conflict blocks save until human
  review. Timezone-aware evidence is compared in America/Sao_Paulo.
- Full backend suite: 1362 passed, 3 skipped; CI critical Ruff checks and
  changed-file E/F lint passed. Full frontend suite: 301 passed; ESLint, build
  and bundle budget passed. Scanner Playwright E2E with real Worker: 2 passed
  (manual and automatic capture/review).
- The three skipped backend tests and absence of physical Android/iPhone
  camera access remain validation limits. No real member record was modified.
- Final CLI deployments (no GitHub push): API
  `4c5a403d-ef04-4a18-b26e-f64e3072667c` and worker
  `625a1075-395b-49d5-a857-d077c08c5617`, both `SUCCESS`. The API returned
  HTTP 200 at `/health/ready`, anonymous `parse-image` returned HTTP 401, the
  pilot frontend returned HTTP 200, and the worker scheduler completed jobs.

## Real-receipt range boundary correction - 2026-09-23

- Reproduced the reported failure transiently with the supplied receipt and
  production AI configuration, without saving or changing a member record.
- A measured value that legitimately equals one reference boundary is now
  accepted unless the evidence actually contains the complete printed range
  without a separate measured occurrence. Degenerate AI ranges are ignored.
- The recovery read no longer marks an already verified primary value as a
  critical conflict. It preserves the primary read and records a nonblocking
  diagnostic warning; verified recovery values can still repair missing or
  invalid primary evidence.
- The same receipt now returns waist-hip ratio 0.86, inorganic salt 2.9 kg,
  muscle mass 23.4 kg and BMR 1366 kcal as accepted values. The only remaining
  critical review is the genuine inconsistency between printed weight, height
  and BMI.
- Parser regression suite: 58 passed. Full backend suite: 1364 passed, 3
  skipped. Railway API deployment `7d12e02e-a0f5-4237-8e48-50ecb7932d04`
  reached `SUCCESS`; the public health endpoint returned `ok` and startup logs
  contained no application error.

## Neutral review styling - 2026-09-23

- Removed yellow decoration from nonblocking OCR suggestions, out-of-range
  values, status pills and capability notices in the body-composition workspace.
- Critical inconsistencies remain red and continue to block saving until they
  are reviewed; extraction, reference ranges and validation behavior are
  unchanged.
- Frontend validation: 301 tests passed, ESLint passed, production build and
  bundle budget passed. Vercel production deployment
  `dpl_CJEeYSpk3ktZFAMBGt4jmJW8xqvF` reached `READY` and was aliased to the pilot
  URL, which returned HTTP 200.

## Value/Range column and adjacent-row correction - 2026-09-24

- Root cause: local OCR could rescue values from neighboring rows and assign
  unlabeled numbers by receipt order. The AI path accepted self-reported text
  evidence containing a Range endpoint or a number from another printed row.
- Removed positional/neighbor inference from local OCR. The API now verifies
  each Tezewa table value with a second image read that excludes the Range
  column, checks label and first same-row number, and leaves disagreements
  empty for explicit human review.
- A fresh receipt clears measurements from a previously selected image, while
  preserving profile data, anthropometry and manual inputs. The UI explains
  specifically when the Value column could not confirm a measurement.
- The supplied receipt was read transiently against the production AI
  configuration without saving an evaluation: salt 2.9 kg, muscle 23.4 kg,
  BMR 1366 kcal and the other ten table values matched the printed Value
  column. Only the receipt's real weight/height/BMI inconsistency required
  review. Temporary image files were removed after validation.
- Full backend suite: 1370 passed, 3 skipped. Full frontend suite: 302 passed.
  Frontend ESLint, production build/bundle budget and targeted Ruff passed.
- Published by CLI without GitHub: Railway API deployment
  `dc35d7a7-f74b-45f9-8de0-7781d089f366` reached SUCCESS. Vercel deployment
  `dpl_UCEg9gQQK7u8rUXsmaZ2hZefkoeH` reached READY and is aliased to the
  pilot URL. Both the pilot assessment route and API readiness returned HTTP
  200. No member evaluation was created or changed for this verification.

## Full bioimpedance audit repair - 2026-09-24

- Prevented unreviewed OCR drafts from Actuar sync and WhatsApp/Kommo delivery;
  replaced-photo updates no longer silently restore an unreadable old weight.
- Made AI and assistant comparisons chronological and method-aware. Restored
  physical age to the V2 PDF and stopped calling the broad device weight range
  “normal.” Corrected technical PDF page bounds and grouped all five eligible
  history charts on one sheet.
- Full backend suite: 1378 passed, 3 skipped. Frontend suite: 302 passed.
  ESLint, production build, bundle budget and scanner/anthropometry Playwright
  tests passed. A four-page PDF was visually inspected and checked for layout
  overflow by an automated print test.
- Published via CLI without GitHub: Railway API
  `11c5436c-41f5-4515-a0ae-469ad796f3ca` and worker
  `2876acd8-1619-4310-abd0-40c6541bca07` reached SUCCESS; Vercel
  `dpl_2QQkCxQwKQ6JDv4FfTmAYjDmRApE` reached READY and is aliased to the
  pilot URL. API `/health/ready` and pilot frontend returned HTTP 200.
- Physical Android/iPhone camera testing remains pending. No production member
  data was modified during validation.
