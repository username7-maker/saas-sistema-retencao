# Feature Specification: Pilot Admin Surfaces Closure

**Feature Branch**: `045-pilot-admin-surfaces-closure`
**Created**: 2026-05-27
**Status**: Draft
**Input**: Reabrir a Phase 4.34 como trilho ativo depois do fechamento de e-mail transacional com Resend.

## User Scenarios & Testing

### Primary User Story

Como owner ou manager do piloto, quero que as superficies administrativas restantes reflitam o estado real do sistema, gerem relatorios sem vazamento entre academias, exibam vazios honestos e permitam administrar metas, notificacoes e usuarios sem contratos quebrados.

### Acceptance Scenarios

1. **Given** um owner dispara o relatorio mensal, **When** o job roda, **Then** somente usuarios de lideranca da mesma academia recebem o e-mail.
2. **Given** uma academia ainda nao tem respostas NPS, **When** a tela NPS abre, **Then** ela explica que o modulo esta operacional mas sem base suficiente.
3. **Given** um owner ou manager acessa Metas, **When** cria/lista/remove uma meta, **Then** o contrato frontend/backend permanece consistente.
4. **Given** notificacoes existem, **When** o usuario abre a central, **Then** autenticacao e RBAC sao preservados sem redirect quebrado.
5. **Given** usuarios sao administrados pelo owner/manager, **When** dados basicos sao editados, **Then** identidade organizacional e RBAC continuam claros.

## Requirements

- **REQ-01**: Disparo mensal de relatorios deve ser tenant-scoped para destinatarios e auditoria.
- **REQ-02**: Relatorios administrativos devem falhar de forma explicita quando o provedor de e-mail ou o dashboard estiver indisponivel.
- **REQ-03**: Metas devem continuar usando os contratos existentes `/api/v1/goals/*`, sem introduzir rota paralela.
- **REQ-04**: NPS deve mostrar empty state operacional, nao uma tela que pareca quebrada.
- **REQ-05**: Notificacoes e Usuarios devem preservar RBAC existente e nao abrir novas permissoes nesta fase.

## Out of Scope

- Bulk update de membros.
- Busca por CPF/telefone.
- Upload real de avatar com storage dedicado.
- Novas automacoes ou envio autonomo por terceiros.

## Risks

- A fase entra sobre um worktree ja muito modificado por fases recentes; as mudancas devem ser pequenas e compatíveis.
- O envio Resend ainda depende de chave rotacionada e dominio `cordex.com` verificado para producao plena.
