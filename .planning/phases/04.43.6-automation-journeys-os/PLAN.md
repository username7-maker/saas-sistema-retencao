# Plano - 04.43.6 Automation Journeys OS

## Objetivo

Entregar jornadas operacionais prontas, melhores que automacoes simples, sem quebrar as regras existentes e sem envio autonomo.

## Corte

1. Formalizar spec e decisao no GSD, Spec Kit e Obsidian.
2. Corrigir contrato atual de automacoes (`send_to_kommo` valido, `ai_evaluate` fora da UI).
3. Criar modelos, schemas, router e servico de `AutomationJourney`.
4. Materializar etapas vencidas como `Task` com `source=automation_journey`.
5. Atualizar Work Queue para devolver outcomes para a jornada.
6. Criar tela de jornadas prontas em `/automations`, mantendo regras avancadas.
7. Validar com testes de contrato e build.

## Guardrails

- Sem envio autonomo de WhatsApp, Kommo, e-mail ou cobranca.
- Tenant isolation por `gym_id`.
- Operador executa pela Work Queue.
- `AutomationRule` atual continua compatível.
- Eventos de jornada sao historico operacional; `AuditLog` segue auditoria tecnica.

