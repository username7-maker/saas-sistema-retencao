# Spec 012 - Task Autopilot / Auto Resolution Engine

## User Story

Como gestor de academia, quero que o sistema resolva automaticamente ocorrencias simples e entregue para humanos apenas excecoes, para reduzir tempo operacional gasto em tasks repetitivas.

## Scope V1

- Event log interno tenant-scoped.
- Actions do Autopilot sem conflitar com automacoes legadas.
- Safety checks e flags por academia.
- Auto-close por eventos reais.
- Envio monitorado iniciado por humano pela Work Queue.
- Auto-send automatico permanece desligado por default.
- Timeline visivel continua em `TaskEvent`.

## Out of Scope

- Envio automatico amplo para leads.
- Canvas visual de automacoes.
- Nova timeline paralela de tasks.
- Substituir Work Queue.
- Cobrança automatica, PIX ou cartão.

## Functional Requirements

- FR-001: Todo evento Autopilot deve ter `gym_id`.
- FR-002: Eventos com `deduplication_key` devem ser idempotentes por academia.
- FR-003: Actions devem suportar status planejado, agendado, aguardando outcome, sucesso, falha, timeout, escalado, cancelado e bloqueado.
- FR-004: Safety deve bloquear sem feature flag, consentimento, horario permitido, cooldown, status invalido, termo sensivel ou duplicidade.
- FR-005: Check-in deve resolver tasks/actions de retencao.
- FR-006: Pagamento confirmado deve resolver tasks/actions financeiras.
- FR-007: WhatsApp inbound simples deve resolver tentativa pendente.
- FR-008: WhatsApp inbound sensivel deve escalar para humano.
- FR-009: Work Queue deve permitir `send-and-wait` para task humana.
- FR-010: Owner/manager devem configurar flags e ver metricas.

## Non-Functional Requirements

- NFR-001: Nenhum acesso cross-tenant.
- NFR-002: Nenhum auto-send sem flag explicita.
- NFR-003: Jobs idempotentes e com lock.
- NFR-004: Compatibilidade com tasks existentes.
- NFR-005: Alembic upgrade deve ser seguro em banco existente.
