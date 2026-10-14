# Camera and spreadsheet reliability — 2026-10-06

Scope: imports-page CSV downloads and scanner startup. Preserve unrelated work and existing capture/review flow.

Mandatory camera acquisition must be independent of optional storage, capability negotiation and device enumeration. Bound optional calls; avoid reopening a live camera on unrelated devicechange events; distinguish permission, hardware and timeout errors.

Downloads must retain the blob URL until the browser can consume it, use a longer bounded export timeout. Preserve auth, tenant scope and CSV protections.

Validation: regression tests, full frontend suite, lint, production build, scanner real-worker E2E and browser download E2E. Publish frontend via CLI, no GitHub. Physical academy webcam remains pending when unavailable.
