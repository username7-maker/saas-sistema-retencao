# Plan - 04.43.10 Regua Tecnica Pos-Avaliacao

## Objetivo

Garantir que toda avaliacao gere tres compromissos tecnicos: treino entregue no D+8, feedback no D+14 e reavaliacao conforme `next_assessment_due`.

## Implementacao

1. Estender `assessment_service` com helper idempotente de regua pos-avaliacao.
2. Criar fontes canonicas:
   - `assessment_training_delivery_check_d8`
   - `assessment_feedback_followup`
   - `assessment_reassessment_due`
3. Resolver responsavel tecnico por `member.preferred_shift` contra `User.work_shift_scope` ou `User.work_shift`.
4. Gravar em `Task.extra_data` os metadados de etapa, turno, origem, avaliacao e `work_queue_visible_from`.
5. Cancelar somente tasks futuras abertas da regua anterior quando nova avaliacao for salva.
6. Atualizar Work Queue para esconder tasks futuras em `do_now` e mostrar etapa tecnica.
7. Adicionar outcomes tecnicos:
   - `training_delivered`
   - `training_missing`
   - `training_adjusted`
   - `feedback_positive`
   - `needs_training_adjustment`
   - `reassessment_scheduled`
8. Atualizar Fila do Professor com CTA contextual.
9. Criar testes focados de assessment e Work Queue.

## Riscos e controles

- Duplicidade de tasks: controlada por `assessment_id + source`.
- Poluicao da fila diaria: controlada por `work_queue_visible_from`.
- Professor errado: melhor esforco por turno; sem match, task fica sem responsavel mas com `owner_role=coach`.
- Historico perdido: tasks antigas concluidas permanecem; apenas futuras abertas sao canceladas.
