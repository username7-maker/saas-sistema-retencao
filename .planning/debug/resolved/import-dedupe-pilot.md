---
status: resolved
trigger: "Investigate pilot member import deduplication after repeated reimports of the same XLSX created duplicate members."
created: 2026-03-26T12:04:48.7400758-03:00
updated: 2026-03-26T12:17:06.2979956-03:00
---

## Current Focus

hypothesis: The import dedupe fix is confirmed in production, and the remaining duplicate rows are historical pilot data that can be cleaned with the one-off reconciliation script.
test: Archive the resolved session, record the production verification numbers, and preserve the cleanup evidence for the pilot tenant.
expecting: The resolved record should show the live Railway preview converged to updates/skips and that cleanup can proceed without checkin collisions.
next_action: Move the session to resolved and append the known pattern to the debug knowledge base.

## Symptoms

expected: Re-previewing the same XLSX should mostly resolve existing members and should not propose creating ~1629 new members again.
actual: Before the fix, preview showed would_create 1629 / would_update 5667 on repeated import; commit created duplicates.
errors: No HTTP error; data-integrity issue.
reproduction: Use pilot gym `ai-gym-os-piloto`, owner auth, and preview `C:\Users\asteriscos\Downloads\Todos os Clientes (1).xlsx` against `/api/v1/imports/members/preview`.
started: Issue surfaced during Phase 4.3 pilot day 0 after wave 2 import on 2026-03-26.

## Eliminated

## Evidence

- timestamp: 2026-03-26T12:04:48.7400758-03:00
  checked: required context files
  found: The import service already routes preview rows through `_resolve_member_from_row(...)`, mutates the in-memory lookup after preview creates, and the parsing test suite includes name-only dedupe coverage.
  implication: The local fix addresses the exact failure mode described in Day 0, so the remaining task is to verify completeness and identify residual gaps or cleanup needs.
- timestamp: 2026-03-26T12:06:27.7235573-03:00
  checked: `preview_members_csv`, `import_members_csv`, `_build_member_lookups`, `_add_member_to_lookups`, and `_resolve_member_from_row`
  found: Both member preview and commit now resolve rows through the same multi-key matcher and both mutate the lookup after each create; commit also re-adds updated members to the lookup after mutation.
  implication: The original stale-lookup bug should be fixed for repeated rows and repeated reimports unless the matcher still misses some real-world row shapes.
- timestamp: 2026-03-26T12:10:46.3230745-03:00
  checked: in-process replay of `C:\Users\asteriscos\Downloads\Todos os Clientes (1).xlsx`
  found: With an empty initial member set, first import produced `7029` creates and `267` updates; a second preview of the same file produced `would_create=0`, `would_update=7296`, and a second import produced `imported=0` with no member-count growth.
  implication: The deployed dedupe change fixes the pilot's original repeated-reimport failure mode for the real XLSX.
- timestamp: 2026-03-26T12:10:46.3230745-03:00
  checked: `_add_member_to_lookups()` behavior when re-adding an already indexed member
  found: Re-adding the same member grows `lookup['by_name'][name_key]` from `1` to `2`, so update-heavy imports duplicate in-memory candidates even when no new member exists.
  implication: This is a residual cleanup/performance issue, not the original data-integrity bug, and it should be fixed before closing the investigation.
- timestamp: 2026-03-26T12:13:14.5779388-03:00
  checked: focused pytest coverage and post-patch real-XLSX replay
  found: `pytest tests/test_import_service_parsing.py -q` passed with `44` tests, and replaying `Todos os Clientes (1).xlsx` still produced `preview2_would_create=0` and `summary2_imported=0` on the second pass.
  implication: The code change is verified locally, and the remaining uncertainty is only the live Railway/pilot environment plus cleanup of duplicates created before the fix.
- timestamp: 2026-03-26T12:17:06.2979956-03:00
  checked: live Railway preview plus pilot dry-run cleanup on `ai-gym-os-piloto`
  found: Re-previewing `Todos os Clientes (1).xlsx` as owner returned `would_create=0`, `would_update=7296`, `would_skip=46`, `ignored_rows=0`; the dry-run cleanup found `3258` suspect duplicates created after `2026-03-26T14:13:00+00:00`, with `55` linked checkins, `20` linked risk alerts, `0` tasks, `0` assessments, and `0` checkin collisions.
  implication: The production environment confirms the repeated-reimport bug is fixed, and the remaining damage is limited to historical duplicate members that can be cleaned safely with the scripted mapping.

## Resolution

root_cause: The original pilot duplicate creation came from preview/import not reusing newly created members in the in-memory lookup; that behavior is now fixed. The remaining cleanup gap is that `_add_member_to_lookups()` re-appends existing members into name buckets on every update.
fix:
  Deduped `_add_member_to_lookups()` name-bucket insertions by member identity/id, routed preview/import through the same row resolver so repeated reimports reuse newly created members, added regression tests for second preview/import replays on name-only rows plus lookup idempotence, and added a cleanup script to quantify/apply one-time repair for pilot duplicates already written before the fix.
verification:
  Focused pytest passed (`44` tests). Post-patch replay of the real XLSX converged on the second pass with zero creates and zero member-count growth. Human verification on Railway for `ai-gym-os-piloto` also converged to `would_create=0`, `would_update=7296`, `would_skip=46`, `ignored_rows=0`, and the dry-run cleanup found no checkin collisions for the historical duplicates.
files_changed:
  - saas-backend/app/services/import_service.py
  - saas-backend/tests/test_import_service_parsing.py
  - saas-backend/scripts/cleanup_member_reimport_duplicates.py
