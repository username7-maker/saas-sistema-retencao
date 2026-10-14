# Member import identity correction — 2026-09-30

## Cause and scope
Weak phone/name/substring matching could select a different member despite conflicting email, CPF or external code. Import then retained a longer existing name while replacing other profile fields.

## Fix
Filter weak candidates by identifier compatibility, including the fuzzy-name fallback. Preserve existing exact-identifier matching and identifier-free compatibility behavior.

## Verification
Four new regression cases failed before the change. Import suite: 77 passed. Complete backend suite with system Python: 1395 passed, 3 skipped. The repository-parent venv initially lacked openpyxl; no application changes were made for that environment failure.

## Pilot repair
Corrected member [member-id-redacted] based on Actuar export and explicit user confirmation of assessment ownership. Preserved member ID, one body-composition evaluation and 18 checkins. Prior identity stored in audit_logs in the same transaction. No historical events moved or deleted.

## Deployment
Railway API CLI deployment bbd7ec21-02ca-42fd-bfe7-39c964c1eebf initiated; no GitHub push. Status must be verified before claiming release.

Deployment verified SUCCESS; production /health/ready returned status ok. Database verification confirmed corrected name/email/Actuar code with one evaluation and 18 checkins preserved.
