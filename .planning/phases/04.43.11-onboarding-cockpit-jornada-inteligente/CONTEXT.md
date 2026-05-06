# 04.43.11 - Onboarding Cockpit e Jornada Inteligente D0-D30

## Contexto

O onboarding atual cria etapas D0/D1/D3/D7/D15/D30 e calcula score, mas ainda gera ruído operacional porque tasks futuras entram na leitura de progresso e podem aparecer junto da fila diária. Também há risco de duplicidade entre o serviço legado de onboarding e jornadas de automação.

## Decisão de Produto

As etapas D0-D30 permanecem. A mudança é operacional: a fila diária mostra apenas ações atuais/vencidas, enquanto a jornada completa continua visível no cockpit, na aba Onboarding e na lista completa.

## Objetivo

Transformar onboarding de uma lista de tasks para uma jornada operacional com score justo, próxima ação clara, deduplicação e auto-fechamento seguro por evidências reais.

## Fora de Escopo

- Envio automático de WhatsApp.
- Exclusão física de tasks antigas.
- Canvas visual de automação.
- Redesenho completo de todo o módulo de Tasks.
