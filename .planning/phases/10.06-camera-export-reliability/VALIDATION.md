# Validation — 2026-10-06

- Frontend: 317 tests passed (59 files). Full ESLint and production build passed, JS bundle budget passed.
- Browser E2E: CSV members/checkins actual service downloads passed with synthetic API fixtures; real-worker scanner manual/automatic and optional startup failures passed (3 cases), including rotation/corners/selection/stream cleanup.
- Startup fixes: optional storage/capability/enumeration errors cannot discard a working stream; optional constraints bounded at 1.5 s; initial permission timeout 30 s; hard frame-rate minimum removed; live stream no longer reopened on unrelated devicechange. Permission/hardware/timeout errors have specific guidance.
- CSV: blob URL released after 60 s rather than immediately; request timeout 120 s instead of global 20 s. Auth and CSV server rules unchanged.
- Vercel frontend production dpl_2p2NayeReTWFXaVuJYAcdmwYTGq8 READY; alias https://saas-frontend-pearl.vercel.app. CLI explicit scope automai required. No GitHub push. Backend unchanged.
- Pilot members exports server returned HTTP 200, ~1.1–3.7 s. Integrated-browser download event timed out before and after patch; an actual pilot file download has NOT been confirmed. Do not claim full production export validation.
- Physical academy webcam validation remains pending; no physical hardware tested.
