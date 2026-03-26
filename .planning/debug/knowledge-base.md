# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## import-dedupe-pilot — repeated pilot XLSX reimports created duplicate members
- **Date:** 2026-03-26
- **Error patterns:** data-integrity issue, duplicate members, repeated import, would_create 1629, would_update 5667, preview created duplicates
- **Root cause:** Preview/import did not consistently reuse newly created members in the in-memory lookup during repeated reimports, and `_add_member_to_lookups()` also re-appended existing members into name buckets on updates.
- **Fix:** Routed preview/import through the same row resolver, made lookup updates idempotent by member identity/id, added regression coverage for second-pass name-only reimports, and added a cleanup script for historical pilot duplicates.
- **Files changed:** saas-backend/app/services/import_service.py, saas-backend/tests/test_import_service_parsing.py, saas-backend/scripts/cleanup_member_reimport_duplicates.py
---
