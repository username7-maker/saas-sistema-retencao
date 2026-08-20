# LEARNINGS — ciclo de aprendizado do time

> Todo smoke que falhou, slot blocked, HTC reprovado ou bug vira entrada aqui
> (causa raiz + regra). O ciclo não rompe.

## 2026-07-08 — smoke baseline falhou: interpretador errado (M1, pré-planejamento)

- **Sintoma:** `python -m pytest saas-backend -q` → ModuleNotFoundError (sqlalchemy) em
  todos os módulos.
- **Causa raiz:** nesta máquina o `python` do PATH (uv 3.11 / hermes venv) não tem as
  deps do projeto; elas estão no Python 3.12 oficial (`py -3.12`).
- **Regra:** smoke do repo é `py -3.12 -m pytest saas-backend -q` (gravado no
  `.ai-team.json`). Worker novo confirma o interpretador ANTES de interpretar falha de
  teste como bug de código.

## 2026-07-08 — motor ai-team assumia `main` como base (M1, pré-build)

- **Sintoma:** `ai-team start/reconcile` hardcodavam `main`; aqui push na `main` do
  GitHub dispara deploy de produção (Railway/Vercel) e a main local estava 135 commits
  atrás da branch viva `pilot-safe/p0-blockers-20260424`.
- **Causa raiz:** o motor nasceu pra repos greenfield (main = integração). Produto em
  produção usa branch de trabalho protegida — premissa não configurável.
- **Regra:** `baseBranch` no `.ai-team.json` (ADR 001). Em produto vivo, SEMPRE conferir
  quais branches disparam deploy antes de qualquer fluxo que crie/mova branches.

## 2026-07-08 — specs assumiram path de API sem conferir o client real (M1, cockpit-ui)

- **Sintoma:** DESIGN-SPEC do frontend assumiu `api.get("/cockpit/daily")`; o client real
  (`dashboardService.ts`) usa caminho completo `"/api/v1/..."` sem prefixo no axios.
- **Causa raiz:** spec escrita a partir do padrão do backend (prefix implícito) sem abrir
  o service análogo do frontend.
- **Regra:** DESIGN-SPEC de consumo de API cita o arquivo análogo do client e copia o
  formato do path dele (worker corrigiu e documentou no ARTIFACTS — sem dano).
