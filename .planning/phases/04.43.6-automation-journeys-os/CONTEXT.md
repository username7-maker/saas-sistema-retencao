# 04.43.6 - Automation Journeys OS

## Contexto

As automacoes atuais do AI Gym OS funcionam como regras simples de gatilho para acao. Isso e util para piloto, mas ainda fica abaixo da promessa do produto: transformar sinais operacionais em execucao diaria mensuravel.

A fase 04.43.6 evolui automacoes para jornadas multi-etapa. O sistema passa a inscrever alunos/leads em fluxos por ciclo de vida, criar tasks acionaveis, registrar eventos e usar Work Queue como superficie principal de execucao.

## Base Real

- `AutomationRule` permanece como regra avancada/legado.
- `Task`, `TaskEvent` e Work Queue ja formam a camada operacional de execucao.
- `FinancialEntry` e a regua de inadimplencia 04.43.5 continuam como fonte financeira.
- Nenhum canal externo deve enviar mensagem automaticamente na V1.

## Decisao

O AI Gym OS deve competir acima de automacoes de disparo. O diferencial da V1 e jornada assistida: sinal -> inscricao -> etapa -> task -> execucao humana -> outcome -> metricas.

