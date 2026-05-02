# Implementation Plan: Automation Journeys OS

## Backend

1. Corrigir `VALID_ACTIONS` para aceitar `send_to_kommo`.
2. Criar modelos:
   - `AutomationJourney`
   - `AutomationJourneyStep`
   - `AutomationJourneyEnrollment`
   - `AutomationJourneyEvent`
3. Criar migration `20260428_0036_add_automation_journeys`.
4. Criar schemas e router `/automation-journeys`.
5. Criar servico de templates, preview, ativacao, processamento e outcome.
6. Integrar job no scheduler.
7. Integrar Work Queue para retornar outcomes a jornadas.

## Frontend

1. Criar service `automationJourneyService`.
2. Criar painel `AutomationJourneysPanel`.
3. Transformar `/automations` em duas abas:
   - Jornadas prontas
   - Regras avancadas
4. Remover gatilho `ai_evaluate` da UI enquanto nao existir contrato real.

## Validation

1. Testes de service/router.
2. Compile backend.
3. Build frontend.
4. `specify check`.

