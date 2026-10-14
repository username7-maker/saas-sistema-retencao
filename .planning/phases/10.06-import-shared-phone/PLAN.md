# Shared phone import identity — 2026-10-06

Fix the reproduced Aluna C/Aluno D collision without modifying unrelated pending work.
Phone alone must never link incompatible names. Member preview and commit must
report an unresolved shared phone row, without creating or updating a member,
when no strong identifier is provided. Exact/compatible names and known strong
identifiers retain their existing behavior. Distinct CPF/email can establish a
separate record. Existing error/pending export contract is reused; no migration.

1. Observe failing regression tests before implementation.
2. Apply a shared matching rule and shared pending-row rule to preview/commit.
3. Verify historical source files against current Aluna C and Aluno D, read-only.
4. Run focused and complete backend tests and changed-file lint.
5. Publish API and worker through CLI without GitHub, verify readiness.
