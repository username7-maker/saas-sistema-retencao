# Validation - Phase 09.22

## Completed locally

- Backend focused coverage: calculation boundaries, Poortmans/Lee eligibility,
  reported-value precedence, provenance response fields, migration behavior,
  32-protocol matrix, reconciliation matching, hash guards and idempotence.
- Backend full suite: 1,224 passed; one pre-existing AI fallback wording assertion failed.
- Frontend focused suite: 34 passed.
- Frontend production build: passed (`tsc -b` and `vite build`).
- Frontend full suite: 203 passed; seven pre-existing page tests failed and the
  environment-dependent audit suite lacked its required URLs.
- Alembic head and migration compilation were checked locally.
- Both local Actuar exports match the approved SHA-256 values exactly.
- New Python files pass Ruff checks apart from intentional CLI output/entry-point
  exceptions and repository-wide legacy line-length debt.

## Production observations

- Recoverable pre-migration snapshot created in
  `codex_backup_20260901_pre_calc`: 140 assessments, 462 body-composition
  evaluations and 11 automation rules (1,808 kB).
- Migration `20260901_0059` applied successfully. Existing device values were
  compared against the snapshot: zero reported muscle or TMB values changed.
- Railway API deployment `528bf8cd-8bbc-4cec-b5ce-49b32445b50e` and worker
  deployment `ef71e762-a84c-4bd8-8dc2-c6f975dc9b62` are healthy.
- Vercel production deployment `dpl_DkX3UwsdbFoqeSKaUxQZid9TM6Kx` is Ready and
  aliased to `https://saas-frontend-pearl.vercel.app`.
- Pinned Actuar reconciliation was validated with a full transactional rollback
  before apply. Applied batch: `c436edc4-fc94-4a46-93e8-ac093d55ce4c`.
  It imported 2,579 check-ins and updated 223 plans and 462 shifts. There are
  zero duplicate member/timestamp keys and 806 member rollback snapshots.
- Post-apply dry-run is idempotent: zero check-ins, plans or shifts proposed.
- The historical CPF encryption key is incompatible with all 5,026 encrypted
  CPFs (`InvalidTag`). Reconciliation therefore used a unique CPF bridge between
  the two pinned exports followed by a unique strong client/database match.
- Three production automation rules were re-enabled after the cooldown deploy;
  preview/demo rules remain disabled. Audit batch:
  `be0c226d-3b38-4327-805a-98bf2ebf582d`.
- Final database size is 328 MB, including the logical backup and the legitimate
  reconciled check-ins.

## Remaining operational follow-up

- Supabase PostgREST still reports `exceed_db_size_quota` at 328 MB. Railway
  continues to use the database successfully (`/health/ready` HTTP 200), but
  restoring direct REST requires a billing/spend-cap or Supabase support action.
- Recover or rotate the historical CPF encryption key through a separately
  reviewed migration; do not overwrite the existing ciphertext in place.
- Keep the pre-migration backup schema until the owner accepts the production
  smoke sample, then remove it in a separate, explicit storage-maintenance run.
- Review the 991 reconciliation report rows that were intentionally excluded
  from automatic apply because they lacked a unique strong match.
