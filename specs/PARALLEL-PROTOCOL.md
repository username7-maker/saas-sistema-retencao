# PARALLEL-PROTOCOL — desenvolvimento multi-agente em worktrees

Como vários Devs (Claudes) trabalham em paralelo neste repo sem merge hell. 5 regras de ouro.
(Adaptado à estrutura real deste produto: `saas-backend/` FastAPI + `saas-frontend/` React.)

## 1. Worktree por worker
Cada Dev trabalha numa cópia isolada do repo em `.worktrees/<worker>/`, na sua própria
branch (`worker/<milestone>/<slot>`). Criada pelo `ai-team start` (em `tools/ai-team`).

## 2. Slot é a unidade de trabalho
`specs/slots/<milestone>/<slot-id>/` com `BRIEF.md` + `DESIGN-SPEC.md` + `CONTRACT.md` +
`STATUS.txt` + (no fim) `ARTIFACTS.md`. Ciclo:
```
available → claimed:<worker> → done → (reconcile) → branch de integração
                              ↘ blocked:<motivo> → CTO/Arquiteto resolve
```
As specs de produto continuam em `specs/NNN-*/` (numeração existente); os slots do time
vivem em `specs/slots/` sem conflitar.

## 3. Zoning rígido (territórios não-sobrepostos)

| Território | Pode editar | Não pode |
|---|---|---|
| **Backend-API** | `saas-backend/app/routers/**`, `app/services/**` (arquivos do seu slot) | `app/core/**`, `app/main.py`, models de outros domínios |
| **Backend-Dados** | `saas-backend/app/models/**`, `alembic/versions/*` (migration nova) | routers/services de outros slots |
| **Frontend** | `saas-frontend/src/pages/**`, `src/components/**`, `src/hooks/**` (do seu slot) | `src/App.tsx`, rotas globais, `src/contexts/**` |
| **Jobs/Integrações** | `saas-backend/app/background_jobs/**`, `app/utils/**` (do seu slot) | `app/core/**` |

**Zonas neutras** (só o Integrador/Reconciler toca): `saas-backend/app/main.py` (registro
de routers), `app/core/**`, `requirements.txt`, `saas-frontend/package.json`,
`src/App.tsx`/rotas globais, `docker-compose*.yml`, workflows do CI, `specs/RESUME.md`.

**Regra de ouro:** se 2 workers podem editar o mesmo arquivo, o arquivo é zona neutra.

## 4. Claim atômico
O worker escreve `STATUS.txt=claimed:<worker>` + `OWNER.txt` e commita na sua branch. Dois
workers no mesmo slot → o segundo pega conflito e escolhe outro. (O `ai-team start` faz isso.)

## 5. Done exige smoke verde
Antes de `done`: o smoke do CONTRACT passa (default do repo em `.ai-team.json`; slots de
frontend incluem também `npm run build` em `saas-frontend`). Escreve `ARTIFACTS.md`
(arquivos, smoke, pendências). O reconciler (`ai-team reconcile`) faz merge `--no-ff`,
resolve zonas neutras (registro de routers, rotas do front), roda o smoke cruzado e limpa
a worktree.

## Papéis
- **Arquiteto** — escreve BRIEF + DESIGN-SPEC dos slots (antes dos Devs). Guardião do EMPRESA.md.
- **Dev/Worker** — pega 1 slot, implementa, smoke, done. Vários em paralelo.
- **Integrador/Reconciler** — merge + review + zonas neutras. Único a tocar a branch de integração.
- **CTO** — fala com o fundador, define milestones. Não toca código.

## Regra extra deste repo (produto EM PRODUÇÃO na ProGym)
A branch de trabalho vigente é a que estiver ativa no repo (hoje: `pilot-safe/*`). O
reconciler NUNCA mergeia direto em `main` sem o gate de produção: testes verdes +
checklist de deploy + aprovação do fundador no HTC. A ProGym usa o sistema no dia a dia —
regressão em retenção, cobrança ou WhatsApp atinge operação real. Na dúvida, não deploya.
