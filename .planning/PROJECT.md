# SaaS Sistema Retencao

## What This Is

Plataforma operacional para academias acompanharem alunos, risco de churn, onboarding, CRM, tarefas e avaliacoes tecnicas em um unico fluxo. Depois do milestone `v3.1.0`, o produto sustenta melhor piloto real e operacao limitada, com superficies mais honestas por papel e leitura operacional mais confiavel.

## Core Value

A equipe da academia precisa confiar que cada tela mostra o estado real do aluno e so oferece acoes que de fato fecham operacionalmente.

## Current State

- **Latest shipped milestone:** `v3.1.0 Prontidao Operacional`
- **Shipped on:** `2026-03-24`
- **Operational target reached:** `piloto + operacao limitada`
- **Key result:** CRM, busca operacional e superficie administrativa ficaram mais coerentes com o backend real

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

- Nada foi descartado permanentemente; os itens fora do milestone atual foram movidos para backlog `999.x`

## Context

- Produto brownfield em FastAPI + SQLAlchemy + React/Vite
- Tag anterior existente no repo: `v3.0.0`
- `v3.1.0` consolidou o uso de GSD com fases, UAT e auditoria formal
- O sistema esta mais maduro para time real, mas continua com backlog claro para importacao assistida, bulk update e busca por dados sensiveis

## Constraints

- **Tech stack**: Manter FastAPI, SQLAlchemy e React existentes
- **Authorization**: Nao expandir permissao de backend para acomodar UI
- **Operational target**: Seguir focado em piloto + operacao limitada, sem redesign amplo
- **Data integrity**: Continuar evoluindo CRM sem migracoes destrutivas precipitadas

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Usar `v3.1.0` como milestone atual | Existe tag `v3.0.0` no repo e este ciclo e incremental | ✓ Good |
| Fechar CRM sem migracao destrutiva | Preserva historico legado enquanto estabiliza a timeline | ✓ Good |
| Tratar matricula via `extra_data.external_id` | Ja e o identificador operacional mais confiavel na base atual | ✓ Good |
| Nao incluir busca por telefone/CPF agora | Dados estao criptografados em repouso e exigem desenho proprio | ✓ Good |

## Next Milestone Goals

- Mapper/reconciliacao manual na importacao
- Bulk update dedicado de membros
- Busca operacional por telefone/CPF com token/hash/index

---
*Last updated: 2026-03-24 after v3.1.0 milestone completion*
