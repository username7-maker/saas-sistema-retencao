# Plan 036 - Cordex Command Center Premium Frontend

## Technical Plan
1. Criar componentes premium tipados e exportados por `ui2`.
2. Atualizar tokens semânticos sem remover `lovable-*`.
3. Refatorar App Shell preservando estado, navegação e permissões.
4. Refatorar dashboard executivo com dados reais e fallback explícito.
5. Padronizar dashboards principais com cards, tabelas, empty states e tooltips premium.
6. Validar com lint, build e testes.

## Risk Control
- Não alterar services.
- Não alterar endpoints.
- Não alterar schemas TypeScript de API.
- Não alterar autenticação ou storage.
- Fazer mudanças em ondas e manter componentes antigos compatíveis.
