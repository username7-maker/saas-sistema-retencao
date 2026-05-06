# Spec 013 - Post Assessment Technical Ladder

## User Story

Como professor responsavel pelo acompanhamento tecnico, quero receber tasks automáticas apos cada avaliacao para garantir treino entregue, feedback e reavaliacao no prazo certo.

## Scope V1

- Criar tres tasks tecnicas por avaliacao salva.
- Usar `assessment.next_assessment_due` para reavaliacao.
- Ocultar tasks futuras da fila diaria ate a janela operacional.
- Usar Work Queue e TaskEvent existentes.
- Nao enviar mensagens automaticamente.

## Functional Requirements

- FR-001: Criar task `assessment_training_delivery_check_d8` com vencimento D+8.
- FR-002: Criar task `assessment_feedback_followup` com vencimento D+14.
- FR-003: Criar task `assessment_reassessment_due` com vencimento em `next_assessment_due`.
- FR-004: Evitar duplicidade por `assessment_id + source`.
- FR-005: Cancelar apenas tasks futuras abertas de regua anterior do mesmo aluno.
- FR-006: Resolver responsavel tecnico por turno quando houver professor compativel.
- FR-007: Gravar `work_queue_visible_from`.
- FR-008: Work Queue deve esconder tasks futuras em `state=do_now`.
- FR-009: Work Queue deve aceitar outcomes tecnicos.
- FR-010: Frontend deve mostrar etapa tecnica e CTA claro.

## Non-Functional Requirements

- NFR-001: Tenant isolation preservado por `gym_id`.
- NFR-002: Criacao de avaliacao continua funcionando sem novo payload.
- NFR-003: Sem envio externo automatico.
- NFR-004: Historico concluido preservado.
