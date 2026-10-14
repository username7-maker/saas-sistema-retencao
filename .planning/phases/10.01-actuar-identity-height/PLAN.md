# Actuar identity and height reliability — 2026-10-01

## Authorized scope
Fix the diagnosed Actuar integration failures. Preserve unrelated pending work. Publish backend through Railway CLI without GitHub.

## Contract
- Registered height is the primary source; weight/BMI derivation remains the legacy fallback, with correct provenance classification.
- An imported numeric code is only a lookup hint. It requires exact code plus independent name, email or CPF evidence; it cannot become a trusted link based only on the code.
- All result sets, including a single result, undergo identity checks. Known conflicts in code, CPF, email or birthdate prevent selection. Name-only selection is insufficient.
- Duplicate identity matches remain unresolved. No schema migration or broad automatic retry.

## Steps
1. Reproduce faults with regression tests.
2. Correct mapping, resolution and candidate selection.
3. Run targeted and complete backend tests; review patch and lint of changed code.
4. Publish API and worker; verify deployment status and API readiness.
5. Inspect pending records where production read access is available. Retrying requires confirmed identity, required fields and no existing external duplicate.

## Constraints
Real Aluno A test exposed legacy test measurements blocking review. Add explicit, reviewed removal of anthropometric fields on update; omitted/blank OCR fields without removal intent remain protected. Do not bypass review or create duplicate evaluations. Publish API before frontend, then verify the same record.

Local direct production database connections currently time out on both pooler ports. Production SSH is not configured. Railway logs remain accessible. Historical count from 30/09 cannot substitute for current queue verification.
