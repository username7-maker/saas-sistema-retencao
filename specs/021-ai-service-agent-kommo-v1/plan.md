# Spec 021 Plan - AI Service Agent Kommo V1

## Technical Approach

Reusar a arquitetura existente de Kommo, Autopilot, Work Queue e contexto canonico. A V1 adiciona uma camada de atendimento assistivo que transforma mensagens inbound em classificacao, rascunho e handoff humano.

## Backend

- `ai_service_agent_service.py`
- `ai_service_agent_policy_service.py`
- `ai_service_agent_safety_service.py`
- `ai_service_agent_prompt_service.py`
- endpoints `/api/v1/ai/service-agent/*` quando necessario
- extensao do webhook Kommo existente
- extensao de settings Kommo/AI

## Frontend

- AI Inbox: filtro e inspector de agente Kommo.
- Tasks/Work Queue: badges e CTA de rascunho.
- Settings: modo `Somente rascunho`, flags e limites.

## Data

Preferir `AutopilotEvent`, `AutopilotAction`, `MessageLog`, `TaskEvent` e `KommoMemberLink`. Criar tabela nova apenas se o payload de draft precisar de historico independente.

## Rollout

1. `draft_only`, sem autoenvio.
2. 30 mensagens reais monitoradas.
3. Ajuste de prompts e bloqueios.
4. Habilitar dominios simples: onboarding, informacao geral e avaliacao.
5. Depois avaliar retencao e financeiro assistido.

