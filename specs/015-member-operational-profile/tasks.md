# Tasks

## Backend

- [x] Criar schemas de perfil operacional.
- [x] Criar service de snapshot operacional.
- [x] Criar service de next best action global.
- [x] Criar service de permissao/visibilidade por role.
- [x] Criar migration e model `member_notes`.
- [x] Criar endpoints de notas estruturadas.
- [x] Criar endpoint `GET /api/v1/members/{member_id}/operational-profile`.
- [x] Integrar tasks filtradas por `member_id`.
- [x] Integrar timeline de `TaskEvent`.
- [x] Integrar timeline de `AutopilotEvent` e `AutopilotAction`.
- [x] Integrar resumo financeiro seguro.
- [x] Integrar resumo comercial seguro.
- [ ] Adicionar testes de tenant isolation.
- [x] Adicionar testes de role visibility.
- [ ] Adicionar testes de next best action.

## Frontend

- [x] Estender `memberService`.
- [x] Atualizar `MemberProfile360Page` para snapshot.
- [x] Remover listagem ampla de tasks no perfil.
- [x] Adicionar card de proxima melhor acao global.
- [ ] Adicionar sinais criticos.
- [x] Adicionar bloco de Autopilot.
- [ ] Atualizar timeline para categorias.
- [x] Migrar notas internas para endpoints estruturados.
- [ ] Adicionar estados loading/empty/error por bloco.

## Validacao

- [x] Rodar testes backend focados.
- [x] Rodar build frontend.
- [ ] Validar 3 alunos reais no piloto.
- [ ] Registrar resultado em `VALIDATION.md`.
