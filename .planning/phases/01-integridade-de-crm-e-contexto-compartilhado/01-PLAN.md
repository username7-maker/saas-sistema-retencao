# Phase 1 Plan

## Workstreams

1. Normalizar leitura de notas de lead no frontend.
2. Trocar textarea destrutiva do drawer de lead por timeline + append-only.
3. Remover fallback silencioso de notas internas locais no `MemberProfile360Page`.
4. Cobrir o fluxo com testes de frontend e backend.

## Acceptance

- Editar lead nao pode destruir historico existente.
- Quick actions e observacoes manuais precisam coexistir no mesmo historico.
- `conversion_handoff` permanece separado do historico comercial.
- Notas internas do `Profile 360` so aparecem quando vierem do backend.
