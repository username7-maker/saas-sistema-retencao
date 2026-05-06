# Plan 018 - Assessment + Coach Workspace Foundation

## Technical Approach

Implementar um payload read-only de Coach Workspace primeiro, depois conectar a UI.

## Backend

- Criar schema `CoachWorkspaceItem`.
- Criar service `coach_workspace_service`.
- Criar router `coach.py` ou reaproveitar namespace operacional existente se houver padrao melhor.
- Endpoint:
  - `GET /api/v1/coach/workspace`
- Filtros:
  - `shift=my_shift|all|morning|afternoon|evening|overnight|unassigned`
  - `lane=all|training_delivery|training_feedback|reassessment|assessment_pending|body_composition_review|training_adjustment|technical_attention`
  - `state=do_now|upcoming|all`
  - `page`, `page_size`

## Payload

Campos minimos:

- `id`
- `member_id`
- `member_name`
- `preferred_shift`
- `lane`
- `lane_label`
- `primary_action_label`
- `reason`
- `due_at`
- `last_assessment_at`
- `last_body_composition_at`
- `task_id`
- `source`
- `evidence`
- `context_path`
- `allowed_outcomes`
- `data_quality_flags`

## Frontend

- Criar ou adaptar a fila `Professor`.
- Mostrar lista curta e detalhe operacional.
- Usar badges de lane/turno.
- Expor outcomes tecnicos rapidos.
- Reaproveitar `WorkExecutionView` quando viavel.

## Tests

- Service por role e turno.
- Lanes tecnicas.
- Exclusao de retencao/recepcao.
- Tenant isolation.
- Build frontend.

## Rollout

1. Publicar sem ocultar telas atuais.
2. Testar com professores por turno.
3. Ajustar lanes e labels com feedback real.
4. Depois decidir se vira entrada principal em `Avaliacoes` ou `Tarefas`.
