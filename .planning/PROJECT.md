# SaaS Sistema Retencao

## What This Is

Plataforma operacional para academias acompanharem alunos, risco de churn, onboarding, CRM, tarefas e avaliacoes tecnicas em um unico fluxo. Depois do milestone `v3.1.0`, o produto sustenta melhor piloto real e operacao limitada, e o novo ciclo `v3.2.0` foca nos fluxos de base de dados que ainda geram mais atrito operacional.

## Core Value

A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.

## Current State

- **Latest shipped milestone:** `v3.1.0 Prontidao Operacional`
- **Shipped on:** `2026-03-24`
- **Operational target reached:** `piloto + operacao limitada`
- **Current milestone in planning:** `v3.2.0 Operacao de Base`

## Requirements

### Validated

- ✓ Contencao de navegacao e rotas por papel ja reduz 403 previsiveis - `v3.0.x`
- ✓ Importacao com preview e confirmacao explicita antes do commit - `v3.0.x`
- ✓ Workspace tecnico de assessments separado por papel - `v3.0.x`
- ✓ Conversao de lead com handoff minimo obrigatorio - `v3.0.x`
- ✓ CRM preserva timeline estruturada de contato sem achatar metadata - `v3.1.0`
- ✓ Busca de membros atende melhor o fluxo de balcao usando nome, email ou matricula - `v3.1.0`
- ✓ Gestao administrativa mostra apenas acoes que o backend realmente sustenta nas superficies auditadas - `v3.1.0`
- ✓ Notas internas do `Profile 360` refletem apenas o estado persistido na API - `v3.1.0`

### Active

- [ ] Importacao permite mapeamento manual/visual de colunas antes do commit
- [ ] Sistema oferece bulk update dedicado fora do fluxo de importacao
- [ ] Busca operacional suporta telefone/CPF com estrategia segura de indexacao

### Out of Scope

- Nenhum item descartado permanentemente; o foco atual e transformar backlog operacional em escopo executavel

## Context

- Produto brownfield em FastAPI + SQLAlchemy + React/Vite
- `v3.1.0` consolidou CRM, busca operacional inicial e superficies administrativas mais honestas
- O maior atrito restante esta na manutencao da base: importar, atualizar e localizar membros por identificadores sensiveis

## Constraints

- **Tech stack**: Manter FastAPI, SQLAlchemy e React existentes
- **Authorization**: Nao expandir permissao de backend para acomodar UI
- **Operational target**: Evoluir de `piloto + operacao limitada` para operacao interna mais robusta
- **Data sensitivity**: Busca por telefone/CPF so entra com estrategia segura de token/hash/index

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Usar `v3.1.0` como milestone atual | Existe tag `v3.0.0` no repo e este ciclo e incremental | ✓ Good |
| Fechar CRM sem migracao destrutiva | Preserva historico legado enquanto estabiliza a timeline | ✓ Good |
| Tratar matricula via `extra_data.external_id` | Ja e o identificador operacional mais confiavel na base atual | ✓ Good |
| Nao incluir busca por telefone/CPF em `v3.1.0` | Dados estao criptografados em repouso e exigem desenho proprio | ✓ Good |
| Abrir `v3.2.0` a partir dos itens `999.x` | O backlog ja capturava exatamente os proximos gargalos operacionais | ✓ Planned |

## Next Milestone Goals

- Mapper/reconciliacao manual na importacao
- Bulk update dedicado de membros
- Busca operacional por telefone/CPF com token/hash/index

---
*Last updated: 2026-03-24 after opening v3.2.0 milestone*
