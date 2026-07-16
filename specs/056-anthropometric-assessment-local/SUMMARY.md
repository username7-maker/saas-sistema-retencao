# Summary - Spec 056

## Outcome

V1 local implementada em worktree isolada `gsd/phase-11-anthropometric-assessment-local`.

O sistema agora possui um modo `Sem bioimpedancia` no fluxo de Nova Avaliacao, com formulario antropometrico, preview backend, confirmacao idempotente, historico, PDF premium e regua D+8/D+14/D+75/D+90.

## Architectural decisions

- `Assessment` e o agregado oficial da V1 antropometrica.
- `BodyCompositionEvaluation` permanece exclusivo do fluxo de bioimpedancia.
- Historico e unificado somente na leitura.
- `anthropometry_snapshot_json` preserva tentativas, politica, entradas, resultados, origens e hash.
- `calculation_hash` e derivado do snapshot canonico.
- Massa muscular permanece indisponivel.
- Actuar, IA, WhatsApp e Kommo nao fazem parte da V1.

## Main files

- `saas-backend/app/services/assessment_anthropometry_service.py`
- `saas-backend/app/services/assessment_anthropometry_report_service.py`
- `saas-backend/app/routers/assessments.py`
- `saas-backend/app/models/assessment.py`
- `saas-backend/alembic/versions/20260716_0050_assessment_anthropometry_local.py`
- `saas-backend/alembic/versions/20260716_0051_assessment_origin_backfill.py`
- `saas-frontend/src/components/assessments/AssessmentRegistrationComposer.tsx`
- `saas-frontend/src/pages/assessments/NewAssessmentPage.tsx`
- `saas-frontend/src/components/assessments/AssessmentTimeline.tsx`

## Out of scope retained

Spec 057 registra o spike/Actuar Core futuro. Spec 058 registra backlog de expansoes. Nenhum desses itens foi implementado incidentalmente na V1.
