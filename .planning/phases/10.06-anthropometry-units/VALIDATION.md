# Validation

- Reproduced the professor's Weltman preview rejection (waist 21.5 cm).
- Before fixes: backend diagnostic regression and frontend centimetre-label
  regression failed as expected. Iliac label regression also failed before fix.
- Shared protocol bounds extracted without changing any bounds or equations.
- Backend returns implausible_measurement with field, minimum, maximum, unit.
- All dynamic protocol circumference labels and repeat attempt accessible names
  include (cm); existing basic/evolution fields already include units. Help text
  distinguishes tape measurements from skinfolds. Iliac name now translated.
- Complete backend: 1426 passed, 3 skipped. Complete frontend: 319 passed, 59 files.
- Final component tests including iliac and error message: 10 passed.
- Full frontend lint/build/bundle budget passed; final changed-file lint passed.
- No student records modified; valid calculations, drafts and preview invalidation
  remain covered by regression suites. The teacher must correct the actual waist
  measurement; no invented value or weakened plausibility validation was used.

CLI publishing, no GitHub: API 8a4de768-5287-4f45-b2c8-ff20e60ddb00;
worker 6815d93b-e7b0-48ee-8e67-e7ff99f02107. Both SUCCESS; API readiness HTTP 200/ok.
Frontend dpl_CeCWr1cnML9bAgB4Xx9uUTAePRtC READY, production alias
https://saas-frontend-pearl.vercel.app. Final typecheck/build/bundle budget and
full frontend lint also passed after the iliac label completion.

## Entire catalog check
Added parameterized rendering checks for each of the 32 supported protocols:
all required cm fields and their three attempts, height and evolution perimetry
show (cm). Component suite now 42 passed; test-file lint clean. Backend catalog
also contains 32 supported protocols; required cm fields are height, waist and
abdomen. Existing muscle circumference coverage remains. This follow-up changed
tests/documentation only, requiring no new product deployment.
