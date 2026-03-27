---
status: resolved
trigger: "Investigate SendGrid 403 in the live pilot environment during Phase 4.3. Summary: The Railway worker is logging repeated `python_http_client.exceptions.ForbiddenError: HTTP Error 403: Forbidden` from `app.utils.email.send_email`. We need to determine whether this is a code bug, a configuration problem (sender/API key), or both, and recommend/fix the safest path for the pilot."
created: 2026-03-26T00:00:00-03:00
updated: 2026-03-26T12:45:00-03:00
---

## Current Focus

hypothesis: A clean deployment containing only the verified local email/risk mitigation will stop the active worker incident by converting unverified-sender 403s into a one-time explicit block instead of repeated opaque tracebacks.
test: Build an isolated deploy directory from `HEAD`, overlay only the tested `email.py` and `risk.py` changes, deploy it to Railway, and confirm the worker container contains the new block-handling code.
expecting: If deployment succeeds and the worker container shows the new helper, the pilot incident is code-mitigated even before SendGrid sender verification is completed.
next_action: create isolated deploy worktree and ship the email/risk mitigation to Railway

## Symptoms

expected: Pilot email flows should either send successfully or fail gracefully without misleading the team.
actual: Worker logs repeated SendGrid 403 Forbidden errors after risk recalculation/automations.
errors: `python_http_client.exceptions.ForbiddenError: HTTP Error 403: Forbidden`
reproduction: Observe live Railway worker logs while risk automations execute in `ai-gym-os-piloto`.
started: Surfaced on 2026-03-26 after pilot day 0 cleanup/risk recalculation.

## Eliminated

## Evidence

- timestamp: 2026-03-26T00:05:00-03:00
  checked: .planning/debug/knowledge-base.md
  found: No prior resolved debug session matches SendGrid/email/403 symptoms.
  implication: This does not look like a known recurring app bug in the project history.

- timestamp: 2026-03-26T00:06:00-03:00
  checked: saas-backend/app/utils/email.py
  found: `send_email()` and `send_email_with_attachment()` build a standard SendGrid `Mail`, call `client.send()`, catch all exceptions, log the traceback, and return `False`.
  implication: The worker should fail gracefully at the call site; the visible incident is repeated provider rejection and low-quality logging, not an uncaught exception crash.

- timestamp: 2026-03-26T00:07:00-03:00
  checked: saas-backend/app/services/risk.py
  found: Risk automations trigger SendGrid sends at 3-day and 10-day inactivity stages, append failed action history when `send_email()` returns `False`, and do not mark audit stages as triggered on failed sends.
  implication: A persistent 403 will keep producing failed email attempts during recalculation runs, which explains repeated worker log noise in the pilot.

- timestamp: 2026-03-26T00:08:00-03:00
  checked: saas-backend/app/core/config.py and repo-wide SendGrid search
  found: The only SendGrid settings are `sendgrid_api_key` and `sendgrid_sender`, defaulting to empty key and `noreply@aigymos.local`; no sender validation or richer provider error extraction exists.
  implication: A misconfigured live sender or restricted API key can produce 403 without any code-level guardrails to surface the exact provider reason or disable pilot email cleanly.

- timestamp: 2026-03-26T00:12:00-03:00
  checked: Railway production service context and worker logs
  found: The linked Railway project is `ai-gym-os-prod` with worker service `ai-gym-os-worker`; both API and worker run with `SENDGRID_API_KEY` present and `SENDGRID_SENDER=automai904@gmail.com`. Worker logs show repeated SendGrid 403s during risk recalculation request `6399b1a5-accf-4074-bb64-3f1237320911`.
  implication: This is not the no-key path; production is attempting real SendGrid sends with a configured sender during batch automations.

- timestamp: 2026-03-26T00:16:00-03:00
  checked: SendGrid API probes using live Railway env values
  found: A sandboxed `/v3/mail/send` probe succeeded with status 200, but a real `/v3/mail/send` probe using `from=automai904@gmail.com` returned 403 with body `The from address does not match a verified Sender Identity.`
  implication: The primary production failure is sender identity configuration, not malformed app payloads or a dead API key.

- timestamp: 2026-03-26T00:18:00-03:00
  checked: SendGrid sender/domain configuration endpoints
  found: `/v3/verified_senders` returned a different sender (`agroraiz.rs@gmail.com`) with `verified=false`, and `/v3/whitelabel/domains` returned an empty list.
  implication: The SendGrid account has no verified single sender matching the configured Gmail address and no authenticated sending domain available for an immediate env-only swap.

- timestamp: 2026-03-26T00:23:00-03:00
  checked: current workspace files and git status
  found: The workspace already contains uncommitted changes in `app/utils/email.py`, `app/services/risk.py`, and tests that introduce `EmailSendResult`, SendGrid block classification, and blocked-stage handling, while production logs still point at the old helper path.
  implication: There is both a configuration problem in SendGrid and a deployment gap for the code-side graceful-degradation fix.

- timestamp: 2026-03-26T00:27:00-03:00
  checked: git diff for `saas-backend/app/utils/email.py`, `saas-backend/app/services/risk.py`, and related tests
  found: The local diff specifically adds SendGrid 403 classification for unverified sender identity, caches a block reason to short-circuit later sends, and marks 3d/10d risk automations as `blocked` while still recording the stage.
  implication: The intended code fix directly addresses the exact production failure mode and prevents repeated futile retries after the first provider block.

- timestamp: 2026-03-26T00:31:00-03:00
  checked: focused pytest run in `saas-backend`
  found: `python -m pytest tests/test_email_utils.py tests/test_risk_rules.py -q` passed with `6 passed in 0.97s`.
  implication: The local mitigation is test-validated and suitable for a narrow deployment.

## Resolution

root_cause: Railway production is using a `SENDGRID_SENDER` that is not backed by a verified Sender Identity or authenticated domain in the SendGrid account, so real mail sends are rejected with 403. During live validation we also found a deploy/runtime issue: the Railway `ai-gym-os-worker` service was starting the API command instead of `python -m app.worker`, which kept durable risk recalculation requests in `pending` and made operational validation noisy.
fix: Deployed the `EmailSendResult` / SendGrid block-classification changes in `app.utils.email` and `app.services.risk` so the pilot degrades gracefully on provider configuration blocks, and updated Railway/Docker runtime dispatch so the worker service starts the scheduler process while the API continues to run `uvicorn`.
verification: Targeted tests passed locally; live pilot validation succeeded. Worker logs now show explicit SendGrid configuration-block warnings instead of repeated 403 tracebacks, and durable recalculation request `9e79d47f-2818-4351-9713-68226caec9ed` progressed from `pending` to `completed`.
files_changed:
  - saas-backend/app/utils/email.py
  - saas-backend/app/services/risk.py
  - saas-backend/railway.toml
  - saas-backend/Dockerfile
  - saas-backend/tests/test_email_utils.py
  - saas-backend/tests/test_risk_rules.py
  - DEPLOY_PILOT_CHECKLIST.md
