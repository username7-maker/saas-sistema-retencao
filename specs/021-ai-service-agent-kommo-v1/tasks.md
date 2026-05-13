# Spec 021 Tasks - AI Service Agent Kommo V1

## Backend

- [x] Mapear webhook Kommo atual e payload de mensagem inbound.
- [x] Criar settings do agente IA por academia.
- [x] Criar service de classificacao e policy do agente.
- [x] Criar safety checks especificos de atendimento.
- [x] Gerar draft estruturado com resposta curta.
- [x] Criar handoff Kommo/Work Queue sem autoenvio.
- [ ] Registrar metricas dedicadas do agente.
- [x] Criar testes de classificacao, settings e draft.

## Frontend

- [x] Exibir itens `Agente Kommo` na Work Queue.
- [x] Adicionar inspector com mensagem recebida e resposta sugerida via Work Queue/Settings.
- [x] Adicionar CTAs `Preparar na Kommo`, `Copiar`, `Assumir`, `Encaminhar` via Work Queue/outcomes.
- [x] Criar settings simples do agente.
- [ ] Adicionar estados empty/error/loading.

## Pilot

- [ ] Configurar Kommo webhook real.
- [ ] Rodar 30 mensagens reais em modo rascunho.
- [ ] Revisar bloqueios sensiveis.
- [ ] Medir tempo medio de resposta.
- [ ] Decidir dominios habilitados para V2.
