# Plano Tecnico

## Backend

- Criar schemas de `MemberOperationalProfile`.
- Criar `member_operational_profile_service.py`.
- Criar `member_next_best_action_service.py`.
- Criar `member_profile_permissions_service.py`.
- Criar modelo e migration `member_notes`.
- Estender `member_timeline_service` ou criar facade agregadora.
- Adicionar endpoint `GET /api/v1/members/{member_id}/operational-profile`.
- Adicionar endpoints de notas estruturadas se necessario:
  - `GET /api/v1/members/{member_id}/notes`
  - `POST /api/v1/members/{member_id}/notes`
  - `PATCH /api/v1/members/{member_id}/notes/{note_id}`
- Reaproveitar `/api/v1/tasks?member_id=...`.
- Reaproveitar `/api/v1/autopilot/timeline`.

## Frontend

- Estender `memberService` com `getOperationalProfile`.
- Atualizar `MemberProfile360Page` para consumir snapshot.
- Remover filtro client-side amplo de tasks.
- Adicionar card de proxima melhor acao global.
- Adicionar sinais criticos.
- Adicionar estado do Autopilot.
- Adicionar timeline filtravel.
- Migrar UI de notas para `member_notes`.

## Testes

- Backend:
  - snapshot por role
  - tenant isolation
  - next best action global
  - notas estruturadas
  - timeline com Autopilot e TaskEvent
  - tasks por `member_id`
- Frontend:
  - renderizacao do snapshot
  - fallback de blocos
  - role visibility basica
  - CTA por next best action

## Rollout

1. Criar endpoint em paralelo ao Perfil 360 atual.
2. Usar snapshot apenas em blocos novos.
3. Migrar tasks e next best action.
4. Migrar timeline.
5. Migrar notas.
6. Validar no piloto antes de remover leituras antigas.
