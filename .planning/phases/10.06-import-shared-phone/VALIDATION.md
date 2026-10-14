# Validation — 2026-10-06

## Root cause
The phone branch returned its sole candidate regardless of name when the incoming
row lacked strong identifiers. The small earlier Aluna C export therefore matched
Aluno D. Reproduced read-only with source XLSX rows and then with failing tests:
4 failures, 1 pass before the fix. No live student imports were submitted.

## Verification
- Focused importer and new shared-phone tests: 85 passed.
- Complete backend after final changes: 1425 passed, 3 skipped; deprecation warnings only.
- New test file Ruff: clean. Changed service lines: no Ruff findings. The existing
  full service retains 85 unrelated lint findings; no broad formatting applied.
- Current Aluno D profile agrees with his own row 698 in today's full Actuar
  export: name, sex, birthday, membership start, plan and raw import metadata.
  Aluna C agrees with row 3048. No historical profile restoration was needed for the
  inspected fields. Earlier row-level snapshots are unavailable, so this does
  not establish that past import attempts never temporarily changed a field.
- Source files were read-only; no existing member, check-in or assessment was changed.

## Delivery
CLI only, no GitHub push. Previous API deployment 8097d5e9-1dab-4fe4-a8cc-8c8108748dc1
and worker fba7001c-3bf8-4e00-9724-14e05b5b533e remain rollback references.
New API: 8d0fe81b-7326-4822-918f-f92d1427f887.
New worker: a63c961f-2e19-4612-a515-1a08c3ba32ab.
Both deployments confirmed SUCCESS. Production `/health/ready` returned HTTP 200,
`{"status":"ok"}` after deployment. Earlier readiness during the old deployment
returned degraded; a previous Redis fallback warning exists from October 5.
Readiness recovered with the new deployment; no cache configuration was changed.
The actual Aluna C row 575 from the older XLSX was also rechecked locally: it now
becomes pending and cannot match Aluno D. This check performed no database writes.
