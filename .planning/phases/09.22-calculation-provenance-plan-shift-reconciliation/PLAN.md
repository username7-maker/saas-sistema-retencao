# Phase 09.22 - Calculation provenance and Actuar reconciliation

## Objective

Unify TMB and muscle-mass calculations across anthropometry and bioimpedance,
preserve device-reported measurements, expose calculation provenance in the UI
and PDFs, and reconcile Actuar plans/check-in-derived shifts only from the two
pinned exports.

## Calculation policy

- TMB uses Schofield-HW for ages 3 through 18 and Mifflin-St Jeor from age 19.
- Device, OCR and explicit manual values are `reported` and always take precedence.
- Adult fallback uses Lee only with age, sex, valid ethnicity, height, weight,
  arm/thigh/calf circumferences and the matching skinfolds.
- Pediatric fallback uses Poortmans only for white students aged 7 through 16.
- Unsupported pediatric cases remain `unavailable`; no extrapolated value is stored.
- Historical non-null bioimpedance values are preserved as `legacy_unknown` unless
  their origin is already known.

## Reconciliation policy

- Inputs are pinned by SHA-256 and row count:
  - `Todos os Clientes.xlsx`: 1,427 rows,
    `D6F244CF5CCE1C56C16FE17231C725C2D9E36EA6DDA2B0BFD2F7039F3E8DF3EF`.
  - `Acessos.xlsx`: 4,391 valid accesses,
    `00E3DDC39C7282160C017E32A87ABDA00A0E511D9C26F7A2B41E70A1CCE3D15A`.
- Automatic matches require unique access code, CPF or email.
- Names never authorize an automatic update without corroboration.
- Empty, generic, `Plano Base` and `LIVRE` values do not replace a plan or invent a shift.
- Annual, semiannual and monthly plan cycles are preserved from the export metadata.
- Apply requires the exact digest of a reviewed dry-run and records a rollback batch.

## Delivery order

1. Add shared calculation engine and provenance columns.
2. Use the engine in both assessment flows and preserve reported values on reprocessing.
3. Surface origins and warnings in registration, history and premium reports.
4. Put weight among the first facts in the premium PDF and keep evaluation deletion available.
5. Add the pinned, dry-run-first Actuar reconciliation command.
6. Validate formulas, all 32 anthropometry protocols, history/report contracts and import audit metadata.
7. Back up production, run and review the real dry-run, then deploy backend/worker and frontend.

## Production gate

Production deployment and reconciliation are blocked while Supabase reports
`exceed_db_size_quota`. No migration or member update is allowed until database
service is restored, a backup is confirmed, and the real dry-run is reviewed.

