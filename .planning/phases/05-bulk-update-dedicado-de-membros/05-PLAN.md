# Phase 5 Plan

## Workstreams

1. Criar contrato backend dedicado para preview e commit de bulk update de membros existentes.
2. Implementar engine de matching e diff por campo, com bloqueio para linhas invalidas, ambiguas ou nao encontradas.
3. Adicionar superficie dedicada de bulk update no modulo de membros, com preview, diff e confirmacao final.
4. Cobrir backend e frontend com testes de preview, bloqueio e commit seguro.

## Acceptance

- O sistema oferece fluxo dedicado de atualizacao em massa fora da importacao inicial.
- Nenhuma escrita acontece antes da confirmacao final.
- O operador consegue ver exatamente quais membros e quais campos vao mudar.
- O commit final e bloqueado quando houver linhas invalidas, ambiguas ou nao encontradas.
- O fluxo nao cria membros nem depende de nome como chave de match.
