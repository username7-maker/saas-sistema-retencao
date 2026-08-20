# 09.20 - Validation

## Planned Gates
- `specify check` - passed before and after implementation.
- `py -3.12 -m pytest -q saas-backend/tests/test_body_composition_anthropometry_service.py` - 8 passed.
- `npm.cmd test -- src/test/bodyCompositionAnthropometryPreview.test.ts src/test/BodyCompositionReportPage.test.tsx` - 8 passed.
- `npm.cmd run lint` - passed with 2 existing warnings in `MethodOsPage.tsx`.
- `npm.cmd run build` - passed.
- `git diff --check` - passed with CRLF warnings only.

## Deployment Gates
- Vercel production deploy para `saas-frontend-pearl.vercel.app` - `dpl_4q7WRf8rP6hqTM9iDRxGf2oZJ4Ws`.
- Railway deploy do backend `ai-gym-os-api` - `0e8448ed-3e42-447f-aaaa-d1d05673b8fe`.
- Smoke HTTP do frontend - `200 OK`.
- Smoke assets `/body-maps/body-map-male.png` e `/body-maps/body-map-female.png` - `200 OK`.
- Smoke backend `/health` e `/health/ready` - `{"status":"ok"}`.
