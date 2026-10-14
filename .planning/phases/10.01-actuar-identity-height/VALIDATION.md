# Validation — 2026-10-01

## Reproduction and tests
- Initial regressions: ten failures, one passing control before implementation.
- Complete backend suite after production-code changes: 1,406 passed, three skipped, 18 existing deprecation warnings.
- Added three further identity controls (duplicate evidence, conflicting full birthdate, name/email match). Final targeted integration suite: 65 passed.
- New regression file passes Ruff. Whole touched legacy files still contain pre-existing Ruff warnings/errors outside changed hunks; no blanket lint cleanup was performed.
- `git diff --check` passed.

## Published without GitHub
- API: `df4230ff-4519-4a63-8239-2415e72e8b03`, verified SUCCESS.
- Worker: `fba7001c-3bf8-4e00-9724-14e05b5b533e`, verified SUCCESS.
- Production `/health/ready`: `status: ok`.
- Worker startup and scheduler execution confirmed in deployment logs.
- Authenticated pilot page and Actuar status endpoint load successfully (HTTP 200). Aluno B's status now renders registered height 172 cm, classification `critical_direct`, alongside the stored previous failed attempt.
- Production Actuar connection test succeeded through the authenticated settings page: "Conexao com o Actuar validada com sucesso. O ambiente esta pronto para tentar o sync automatico da bioimpedancia."

## Remaining operational work
Historical needs-review jobs do not automatically retry. Conflicting identities and genuinely missing measurements still require review. No broad retry, manual-success flag, or new evaluation was created during verification. The direct database connection timed out on both pooler ports; current total backlog was not re-counted.

## Aluno A live test and additional fixes
- User confirmed the existing 16/09 evaluation: 99 kg, 179 cm, 31.15% body fat, 62.4 kg muscle. Existing evaluation ID `[evaluation-id-redacted]`; no new record.
- Initial save returned HTTP 200 but did not enqueue: legacy circumference values of 12 cm and optional anthropometry flags kept `needs_review=true`. User identified waist, abdomen and hip as test data and requested removal. Iliac circumference is also 12 cm; clarification requested.
- Explicit reviewed anthropometry removal added on update. Omitted or blank OCR values remain protected without an explicit removal list. Unknown/non-anthropometric fields, unreviewed removal and conflicting non-null values are rejected.
- Reproduced a second fault: official bioimpedance with optional incomplete perimetry was blocked by `anthropometry_incomplete`/`anthropometry_protocol_manual_only`. These two coverage flags no longer block when the selected official source is bioimpedance and the protocol is the manual bioimpedance catalog option or absent. Impossible measurements and other selected calculation protocols still require review.
- Complete backend suite: 1,416 passed, three skipped. Complete frontend suite: 313 passed in 58 files. Production build/bundle budget and targeted ESLint passed. Additional end-to-end service regression for explicit removal: 37 body-composition tests passed.
- API follow-up deployment `8097d5e9-1dab-4fe4-a8cc-8c8108748dc1`: SUCCESS; `/health/ready` reports `ok`. No GitHub push.
- Frontend follow-up deployment `dpl_Hi7PxST4Z7W5FoA25567BnsgSD4b`: READY; production alias `https://saas-frontend-pearl.vercel.app` updated. Browser loaded the corrected deployment.
- User-authorized waist, abdomen and hip test values were removed from the same evaluation. Save-only update returned HTTP 200 at 13:17:03 UTC; reopening stored evaluation confirms blank values and preserves iliac 12 cm pending clarification. Official source changed to the confirmed bioimpedance percentage. No external job/success was fabricated. Actual Actuar submission remains incomplete while the additional impossible iliac measurement awaits clarification.
- Evidence: workspace `outputs/teste-aluno-medidas-2026-10-01.jpg`. Browser tab preserved for follow-up.
