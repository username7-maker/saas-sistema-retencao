# Feature Specification: Durable Jobs Closeout

**Feature Branch**: `003-durable-jobs-closeout`  
**Created**: 2026-04-16  
**Status**: Completed  
**Input**: User description: "Continuar a 4.38 fechando o contrato observavel dos jobs criticos e o close-out da fila duravel."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scheduler critico usa fila duravel de forma uniforme (Priority: P1)

Como owner da operacao, eu preciso que os jobs criticos do core usem o mesmo contrato duravel tanto em disparo manual quanto automatico, para que retry, tentativas e falhas nao dependam de qual superficie iniciou o trabalho.

**Why this priority**: Enquanto o scheduler automatico executar partes do core fora do envelope duravel, a fase 4.38 continua incompleta e o piloto segue com comportamento desigual entre "botao manual" e "rotina automatica".

**Independent Test**: Pode ser testado disparando o scheduler de NPS e relatorios mensais em isolamento e verificando que ele enfileira `CoreAsyncJob` por academia, em vez de executar diretamente o side effect.

**Acceptance Scenarios**:

1. **Given** uma academia ativa no scheduler diario de NPS, **When** o job roda, **Then** o sistema cria ou reaproveita um `CoreAsyncJob` de `nps_dispatch` para aquele tenant em vez de enviar os emails diretamente.
2. **Given** uma academia ativa no scheduler mensal de relatorios, **When** o job roda, **Then** o sistema cria ou reaproveita um `CoreAsyncJob` de `monthly_reports_dispatch` para aquele tenant em vez de enviar os emails diretamente.

---

### User Story 2 - Jobs criticos expostos com observabilidade suficiente (Priority: P2)

Como gestor do piloto, eu preciso inspecionar status, tentativas e tempo de espera dos jobs criticos, para que seja possivel diagnosticar atraso, retry e falha sem depender de leitura informal de logs.

**Why this priority**: Sem observabilidade uniforme, a plataforma ainda nao consegue sustentar o gate operacional da fase 4.38.

**Independent Test**: Pode ser testado consultando os status dos jobs criticos e verificando que o payload serializado inclui o contrato minimo da fase, incluindo espera em fila quando aplicavel.

**Acceptance Scenarios**:

1. **Given** um `CoreAsyncJob` critico ja iniciado, **When** o status e serializado, **Then** o payload inclui tipo, status, tentativas, timestamps, erro redigido e `queue_wait_seconds`.
2. **Given** um job critico falha e entra em retry, **When** o worker marca a transicao, **Then** a observabilidade registra a tentativa, o erro redigido e o proximo retry sem depender apenas de excecao crua.

---

### User Story 3 - Webhook setup do WhatsApp deixa de ser job opaco (Priority: P3)

Como operador da academia, eu preciso enxergar o estado do job que configura o webhook do WhatsApp, para que um problema de setup nao fique escondido atras de um QR code aparentemente valido.

**Why this priority**: `whatsapp_webhook_setup` esta no conjunto de jobs criticos da fase, mas hoje ainda nao e realmente consultavel pelo produto.

**Independent Test**: Pode ser testado chamando a conexao do WhatsApp, capturando o `job_id` retornado e consultando a rota de status dedicada.

**Acceptance Scenarios**:

1. **Given** uma conexao WhatsApp iniciada com webhook configuravel, **When** o endpoint `/whatsapp/connect` responde, **Then** a resposta inclui `job_id` e `job_status` do setup quando um job duravel for criado.
2. **Given** um `job_id` de `whatsapp_webhook_setup`, **When** o operador consulta o status, **Then** o sistema retorna o contrato padronizado do `CoreAsyncJob` e rejeita tipos de job incorretos.

---

### Edge Cases

- Como o scheduler se comporta quando um job automatico encontra um `CoreAsyncJob` identico ainda pendente ou em retry para o mesmo tenant?
- O que acontece quando um job ja possui `started_at`, mas a consulta de status ainda precisa expor o tempo inicial de espera em fila?
- Como o produto diferencia um QR code valido de uma configuracao de webhook ainda pendente ou falha?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST usar `CoreAsyncJob` para `nps_dispatch` tanto em disparo manual quanto no scheduler automatico.
- **FR-002**: O sistema MUST usar `CoreAsyncJob` para `monthly_reports_dispatch` tanto em disparo manual quanto no scheduler automatico.
- **FR-003**: O sistema MUST manter deduplicacao por tenant para jobs criticos automaticos quando ja existir job pendente, em processamento ou com retry agendado.
- **FR-004**: O sistema MUST serializar `queue_wait_seconds` para jobs criticos quando o job ja tiver sido iniciado.
- **FR-005**: O sistema MUST emitir telemetria estruturada nas transicoes principais de `CoreAsyncJob` relevantes para o piloto.
- **FR-006**: O sistema MUST expor o status de `whatsapp_webhook_setup` no mesmo contrato padronizado dos demais jobs criticos.
- **FR-007**: O sistema MUST retornar `job_id` e `job_status` no inicio da conexao WhatsApp quando o webhook setup for enfileirado.
- **FR-008**: O sistema MUST preservar o escopo multi-tenant atual e nao misturar jobs de academias diferentes durante enfileiramento e consulta.

### Key Entities *(include if feature involves data)*

- **CoreAsyncJob**: registro duravel de trabalho critico com status, tentativa, erro redigido, timestamps e payload.
- **Scheduler-triggered critical job**: rotina automatica que nao deve executar side effect critico diretamente, mas apenas enfileirar o job duravel correspondente.
- **Queue wait**: intervalo entre `created_at` e `started_at` usado para orcamento e observabilidade do piloto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos jobs criticos listados para `CoreAsyncJob` no milestone atual passam a usar o mesmo envelope duravel em disparo automatico e manual.
- **SC-002**: 100% dos endpoints de status de jobs criticos expostos nesta fatia retornam `status`, `attempt_count`, `error_code`, `error_message`, timestamps e `queue_wait_seconds` quando aplicavel.
- **SC-003**: O workflow de conexao WhatsApp deixa de ter job opaco e passa a expor status consultavel para o webhook setup.

## Assumptions

- O close-out da `4.38` continua limitado aos jobs criticos do piloto ja identificados no GSD.
- Esta spec nao reabre o debate de broker externo; a fila duravel continua baseada em Postgres.
- `public_diagnosis`, `lead_proposal_dispatch` e `whatsapp_webhook_setup` ja possuem base duravel suficiente e so precisam de fechamento de observabilidade/consistencia, nao de uma segunda arquitetura.
