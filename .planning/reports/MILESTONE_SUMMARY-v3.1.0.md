# Milestone v3.1.0 - Project Summary

**Generated:** 2026-03-24
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

`v3.1.0 Prontidao Operacional` fechou os gaps mais urgentes para manter o produto em `piloto + operacao limitada` com mais honestidade operacional.

O foco do ciclo foi simples: parar de prometer na interface o que nao fechava no backend e endurecer os pontos que mais quebravam a rotina da academia.

Os tres temas do milestone foram:
- CRM confiavel para historico comercial e handoff
- Busca operacional de membros para balcao e gestao
- Superficie administrativa coerente com `owner` e `manager`

## 2. Architecture & Technical Decisions

- **Decision:** manter `Lead.notes` como timeline canonica de eventos
  - **Why:** o historico comercial nao podia mais ser achatado por edicao de textarea
  - **Phase:** 1
- **Decision:** normalizar leitura de notas legadas e estruturadas no frontend
  - **Why:** preservar compatibilidade sem migracao destrutiva
  - **Phase:** 1
- **Decision:** remover persistencia silenciosa via `localStorage` no `Profile 360`
  - **Why:** contexto compartilhado precisa refletir apenas o que a API realmente persiste
  - **Phase:** 1
- **Decision:** reaproveitar `external_id` como matricula operacional
  - **Why:** ja era o identificador mais confiavel para balcao sem abrir nova modelagem
  - **Phase:** 2
- **Decision:** expor filtros operacionais usando endpoints existentes
  - **Why:** entregar valor rapido para recepcao e gerencia sem redesenho grande
  - **Phase:** 2
- **Decision:** esconder CTAs owner-only em automacoes para `manager`
  - **Why:** manter o principio de superficie verdadeira em vez de expandir permissao de backend
  - **Phase:** 3

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 1 | Integridade de CRM e contexto compartilhado | Complete | CRM e `Profile 360` passaram a refletir historico e contexto reais |
| 2 | Balcao real: busca de aluno e filtros operacionais | Complete | Busca por matricula e filtros de inatividade/provisorio chegaram na lista de membros |
| 3 | Superficie verdadeira em administracao | Complete | Automacoes e users ficaram mais coerentes com `owner` vs `manager` |

## 4. Requirements Coverage

- [x] CRM-01 a CRM-04: historico comercial preservado e handoff mantido
- [x] CTX-01 a CTX-02: notas internas refletem apenas estado persistido
- [x] LOOK-01 a LOOK-04: busca de membros e filtros operacionais entregues
- [x] ADMIN-01 a ADMIN-03: superficie administrativa auditada e linguagem de usuarios corrigida

**Audit verdict:** `passed` no milestone audit e `passed_with_backlog` no UAT audit.

## 5. Key Decisions Log

- **Phase 1:** parar de sobrescrever `notes` no drawer de lead e tratar novas observacoes como append-only
- **Phase 1:** assumir API-only para notas internas compartilhadas do `Profile 360`
- **Phase 2:** ampliar busca via `external_id` antes de encarar telefone/CPF
- **Phase 2:** deixar telefone/CPF para milestone futuro por exigirem estrategia segura de indexacao
- **Phase 3:** resolver inconsistencias de role escondendo acoes proibidas, e nao flexibilizando backend

## 6. Tech Debt & Deferred Items

- Import mapper e reconciliacao manual ficaram no backlog como `999.1`
- Bulk update dedicado de membros ficou no backlog como `999.2`
- Busca operacional por telefone e CPF ficou no backlog como `999.3`
- O milestone consolidou `piloto + operacao limitada`, mas ainda nao fecha operacao diaria completa de academia

## 7. Getting Started

- **Run the project:** frontend em Vite e backend em FastAPI no workspace principal
- **Key directories:** `saas-frontend/src`, `saas-backend/app`, `.planning/`
- **Tests:** `pytest saas-backend/tests/...` e `npm.cmd run test -- ...`
- **Where to look first:**
  - CRM: `saas-frontend/src/pages/crm/CrmPage.tsx`
  - Member lookup: `saas-frontend/src/pages/members/MembersPage.tsx`
  - Assessments: `saas-frontend/src/pages/assessments/MemberProfile360Page.tsx`
  - Admin surfaces: `saas-frontend/src/pages/automations/AutomationsPage.tsx` e `saas-frontend/src/pages/settings/UsersPage.tsx`

---

## Stats

- **Timeline:** 2026-03-24 -> 2026-03-24
- **Phases:** 3 / 3 complete
- **Status:** shipped and archived as `v3.1.0`
- **Deferred items:** 3 backlog phases promoted for the next cycle
