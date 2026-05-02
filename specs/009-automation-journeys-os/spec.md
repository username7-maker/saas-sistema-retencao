# Feature Spec: Automation Journeys OS

## User Story

Como gestor da academia, quero configurar jornadas operacionais prontas para onboarding, retencao, inadimplencia, NPS, renovacao e comercial, para que o sistema crie a proxima melhor acao na fila da equipe e registre se funcionou.

## Scope

### Included

- Jornadas multi-etapa baseadas em templates.
- Inscricao de alunos/leads elegiveis por tenant.
- Etapas com delay, condicao, canal sugerido, responsavel/cargo, turno e severidade.
- Eventos de jornada com entrada, etapa, task criada, outcome, erro e saida.
- Processamento seguro por job com idempotencia.
- Integracao com Tasks e Work Queue.
- Tela de `Jornadas prontas` em `/automations`.
- Regras antigas preservadas como `Regras avancadas`.

### Excluded

- Canvas visual de workflow.
- Envio autonomo de WhatsApp, Kommo, e-mail, SMS, push ou cobranca.
- Cobranca automatica, PIX ou cartao recorrente.
- IA generativa executando acao sem aprovacao humana.

## Requirements

### R1 - Templates

O sistema deve entregar templates V1:

- Onboarding D0-D30
- Retencao por ausencia
- NPS detrator
- Renovacao
- Inadimplencia
- Comercial
- Promotores e upsell

### R2 - Activation

Ativar uma jornada deve inscrever apenas membros/leads elegiveis do `gym_id` do usuario, sem criar task no preview.

### R3 - Processing

Etapa vencida deve criar ou reutilizar uma task operacional com `extra_data.source = automation_journey` e idempotency key da jornada/enrollment/etapa.

### R4 - Work Queue

A execucao ocorre pela Work Queue. Outcome registrado em task deve atualizar o enrollment e criar `AutomationJourneyEvent`.

### R5 - Guardrails

Sem consentimento ou canal pronto, a etapa vira fallback manual/degradado. Nenhuma mensagem externa e enviada automaticamente.

### R6 - Compatibility

`AutomationRule` continua funcionando como regra avancada. O desalinhamento `send_to_kommo` deve ser corrigido e `ai_evaluate` nao deve aparecer como gatilho se nao houver backend real.

## Acceptance Criteria

- Criar jornada por template.
- Preview retorna quantidade e amostra de elegiveis sem side effect.
- Ativar jornada cria enrollments tenant-safe.
- Job cria task de etapa vencida e evento de jornada.
- Rodar job duas vezes nao duplica task.
- Outcome da Work Queue atualiza enrollment.
- Regras avancadas continuam listando e executando.
- UI de automacoes abre com jornadas prontas como caminho principal.

