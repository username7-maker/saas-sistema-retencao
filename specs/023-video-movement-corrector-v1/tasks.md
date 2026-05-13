# Spec 023 Tasks - Video Movement Corrector V1

## Backend

- [x] Criar settings `movement_video_ai`.
- [x] Criar model/migration `MovementVideoReview`.
- [x] Adicionar filtro global tenant-scoped.
- [x] Criar schemas.
- [x] Criar service de review.
- [x] Criar guardrails de safety no service V1.
- [x] Criar analysis service com modo manual/fallback.
- [x] Criar endpoints.
- [ ] Integrar TaskEvent.
- [x] Integrar AutopilotAction para draft aprovado.
- [x] Integrar Kommo handoff.
- [x] Testar consentimento, bloqueios e estados.
- [ ] Testar tenant com DB/integracao.

## Frontend

- [x] Adicionar settings.
- [x] Adicionar bloco no Coach Workspace.
- [x] Adicionar secao no Perfil 360.
- [x] Adicionar lista de reviews.
- [x] Adicionar fluxo de rejeitar na UI.
- [x] Adicionar fluxo de criar/analisar/aprovar/preparar Kommo.
- [x] Mostrar safety copy.
- [x] Mostrar estados loading/error basicos.

## Pilot

- [ ] Selecionar 10 videos reais.
- [ ] Validar qualidade minima de video.
- [ ] Validar professor revisando feedback.
- [ ] Medir tempo de revisao.
- [ ] Decidir V2: tempo real, app do aluno ou biblioteca de exercicios.
