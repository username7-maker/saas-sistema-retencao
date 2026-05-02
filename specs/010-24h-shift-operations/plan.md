# Plan: Operacao 24h por Turno Real

## Technical Approach

- Estender normalizacao central de `preferred_shift`.
- Reutilizar sync existente de turnos por check-in.
- Adicionar filtro JSONB para esconder `operational_archive` por padrao.
- Implementar cleanup em service layer tenant-safe.
- Atualizar UI com opcoes `Madrugada`.

## Contracts

- `GET /api/v1/tasks/operational-cleanup/preview`
- `POST /api/v1/tasks/operational-cleanup/apply`
- `GET /api/v1/work-queue/items?shift=overnight`
- `GET /api/v1/work-queue/items?shift=my_shift`

## Risk Controls

- Arquivamento nao altera status.
- Preview obrigatorio antes do apply na UI.
- Cleanup restrito a owner/manager.
- Tenant isolation por `gym_id`.
