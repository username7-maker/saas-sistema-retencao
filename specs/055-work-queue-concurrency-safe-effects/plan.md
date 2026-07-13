# Plan 055 - Work Queue Concurrency and Safe External Effects

## Wave 1 - PostgreSQL Harness and Canonical Dedupe

1. Criar harness de teste com PostgreSQL real e duas sessions.
2. Auditar duplicatas sem apagar historico.
3. Adicionar chave canonica tenant-scoped para task ativa e rollout expand/contract.

## Wave 2 - Claim Sidecar and CAS

1. Criar sidecar de coordenacao unico por `gym_id + source_type + source_id`.
2. Expor claimant, versao e precondicao no contrato.
3. Aplicar CAS em execute/outcome com conflito 409 e auditoria persistente.

## Wave 3 - Durable Effect Intent

1. Avaliar consentimento por canal/efeito/finalidade.
2. Persistir intent idempotente e commitar antes do provider.
3. Reservar dispatch, chamar provider fora da transacao e persistir resultado/estado incerto.
4. Validar zero/uma chamada com provider sintetico e rollout aditivo.
