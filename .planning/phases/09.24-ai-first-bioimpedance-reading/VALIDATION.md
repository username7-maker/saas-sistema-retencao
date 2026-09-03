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

Pending commit, Railway API/worker deployment, Vercel deployment and smoke.
