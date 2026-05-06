# Task Autopilot / Auto Resolution Engine

## Visao geral

O Task Autopilot reduz tasks humanas ao registrar eventos reais, aplicar safety checks e resolver automaticamente casos simples. A Work Queue continua sendo a entrada principal da equipe; o Autopilot apenas fecha, aguarda, bloqueia ou escala antes que a fila vire ruido.

## Entidades

- `autopilot_events`: event log interno por `gym_id`.
- `autopilot_actions`: tentativas planejadas/executadas pelo Autopilot.
- `gym_autopilot_settings`: flags e limites por academia.
- `task_events`: timeline operacional visivel para equipe.

## Flags principais

- `autopilot_enabled`: liga a camada.
- `autopilot_auto_close_enabled`: permite fechar tasks por evento real.
- `autopilot_auto_send_enabled`: permite envio automatico quando todos os checks passam.
- `*_enabled`: habilita dominios como retencao, financeiro, onboarding e avaliacoes.

Defaults seguros:

- Autopilot desligado.
- Auto-close ligado quando Autopilot for ativado.
- Auto-send desligado.
- Horario permitido `08:00-20:00`.
- Limite semanal baixo de mensagens.

## Eventos V1

- `whatsapp_inbound_received`
- `whatsapp_outbound_sent`
- `whatsapp_outbound_failed`
- `kommo_handoff_created`
- `kommo_handoff_failed`
- `kommo_inbound_received`
- `member_checkin_created`
- `member_payment_confirmed`
- `member_assessment_scheduled`
- `member_assessment_completed`
- `lead_stage_changed`
- `lead_won`
- `lead_lost`

## Kommo como canal operacional

A fase `04.43.14` permite configurar a Kommo como canal principal de comunicacao operacional.

Regras V1:

- O AI Gym OS nao faz envio autonomo pela Kommo.
- A Work Queue cria/atualiza contato/lead e cria uma tarefa na Kommo com contexto, mensagem pronta e link de retorno.
- O operador confirma e envia pelo ambiente da Kommo.
- O webhook `/api/v1/kommo/webhook` registra respostas como `kommo_inbound_received`.
- Respostas simples podem fechar tasks/actions quando `kommo_auto_close_enabled=true`.
- Mensagens sensiveis continuam escalando para humano.
- Se a Kommo estiver indisponivel, o roteador usa `kommo_fallback_channel`, por padrao WhatsApp.

Flags e settings relacionados:

- `primary_message_channel`: `kommo`, `whatsapp` ou `manual`.
- `kommo_operator_confirmed_send_enabled`: mantem o fluxo humano-confirmado.
- `kommo_auto_close_enabled`: habilita auto-fechamento seguro por eventos Kommo.
- `kommo_fallback_channel`: `whatsapp` ou `manual`.
- `KOMMO_WEBHOOK_TOKEN`: token obrigatorio para aceitar webhooks da Kommo.
- `automation_action_created`
- `automation_action_succeeded`
- `automation_action_failed`
- `automation_action_timed_out`
- `human_intervention_required`

## Safety checks

O Autopilot bloqueia ou agenda quando encontra:

- feature flag desligada
- dominio desligado
- auto-send desligado
- falta de consentimento WhatsApp do membro
- lead sem consentimento formalizado na V1
- fora do horario permitido
- limite semanal de mensagens
- action duplicada pendente
- atividade humana recente
- aluno cancelado
- lead ganho/perdido
- termos sensiveis como cancelamento, contestacao, lesao, emergencia ou pedido de humano

## Rollout recomendado

1. Ativar `autopilot_enabled=true` e manter `autopilot_auto_send_enabled=false`.
2. Validar auto-close com check-in, pagamento, WhatsApp inbound e lead won/lost.
3. Usar `Enviar e aguardar` na Work Queue para envio humano monitorado.
4. Avaliar auto-send apenas para templates seguros como `retention_d3` e `onboarding_d0`.
5. Monitorar metricas: auto-resolvidas, escaladas, bloqueadas e taxa de resolucao.

## Como validar manualmente

### Check-in fecha retencao

1. Criar task de retencao aberta para um aluno.
2. Criar check-in para esse aluno.
3. Confirmar que a task foi concluida e recebeu `TaskEvent` com `source=autopilot`.

### Pagamento fecha financeiro

1. Criar task financeira aberta.
2. Marcar recebivel do aluno como `paid`.
3. Confirmar outcome `payment_confirmed`.

### WhatsApp inbound simples

1. Criar action/task aguardando resposta.
2. Registrar webhook inbound sem termos sensiveis.
3. Confirmar action `succeeded` e task resolvida.

### WhatsApp inbound sensivel

1. Registrar mensagem como `quero cancelar`.
2. Confirmar que o Autopilot cria/escalona task humana urgente.

## Debug

- Eventos: `GET /api/v1/autopilot/events`
- Actions: `GET /api/v1/autopilot/actions`
- Timeline: `GET /api/v1/autopilot/timeline?member_id=...`
- Metricas: `GET /api/v1/autopilot/metrics`
- Settings: `GET /api/v1/settings/autopilot`
