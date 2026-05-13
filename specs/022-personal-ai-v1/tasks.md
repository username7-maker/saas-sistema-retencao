# Spec 022 Tasks - Personal IA V1

## Backend

- [x] Criar schemas de settings, contexto e draft.
- [x] Criar settings `personal_ai`.
- [x] Criar `PersonalAiContext`.
- [x] Criar safety service deterministico V1.
- [x] Criar service de draft supervisionado.
- [x] Criar endpoints `/api/v1/settings/personal-ai`.
- [x] Criar endpoints `/api/v1/members/{member_id}/personal-ai/*`.
- [x] Integrar `prepare-kommo`.
- [ ] Integrar Work Queue source `personal_ai`.
- [x] Registrar auditoria/trilha basica.
- [x] Criar testes focados de settings, classificacao, bloqueios e serializacao.

## Frontend

- [x] Adicionar Settings `Personal IA`.
- [x] Adicionar bloco no perfil do aluno.
- [x] Adicionar bloco no Coach Workspace.
- [ ] Adicionar itens `Personal IA` na Work Queue.
- [x] Mostrar evidencias e bloqueios em rascunhos recentes.
- [ ] Adicionar CTAs de revisar/preparar/copiar/rejeitar.
- [ ] Criar estados empty/loading/error.

## Pilot

- [ ] Habilitar para professores.
- [ ] Testar 20 casos reais.
- [ ] Medir aproveitamento.
- [ ] Revisar bloqueios.
- [ ] Decidir V2: aluno direto, app ou video.
