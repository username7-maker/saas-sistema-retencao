# Plano

## Objetivo

Criar uma regua operacional de inadimplencia que materializa recebiveis vencidos em tasks, aparece na fila de execucao e registra outcomes financeiros.

## Cortes

1. Backend: servico de inadimplencia, schemas, endpoints e worker.
2. Work Queue: dominio finance, outcomes e regras de acesso.
3. Frontend: execucao rapida e painel financeiro de apoio.
4. Validacao: testes backend + build frontend.

## Guardrails

- Multi-tenant por `gym_id`.
- Nenhuma acao externa automatica.
- `trainer` nao acessa financeiro.
- `TaskEvent` e ledger operacional; `AuditLog` segue auditoria tecnica.
