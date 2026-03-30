# Phase 6 Plan

## Workstreams

1. Adicionar colunas hash/indexadas para `phone` e `cpf` em `members`.
2. Centralizar normalizacao e derivacao de hashes sensiveis no backend.
3. Atualizar criacao, edicao e importacao de membros para manter os hashes consistentes.
4. Estender a busca operacional de `members` e da fila de `assessments` para aceitar telefone/CPF com match exato seguro.
5. Integrar a busca nas telas de Membros e Avaliacoes usando o header search contextual e validar com testes.

## Acceptance

- Telefone e CPF podem ser buscados operacionalmente sem descriptografar tudo em Python.
- A busca continua isolada por `gym_id`.
- Criacao, edicao e importacao atualizam hashes automaticamente.
- `Members` e `Assessments` aceitam busca por nome/email/plano e tambem por telefone/CPF.
- O header search contextual das duas telas escreve/le o `?search=` na URL.
