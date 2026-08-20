# ADR 001 — Branch de integração configurável no ai-team (baseBranch)

**Data:** 2026-07-08 · **Status:** aceito · **Decisor:** Arquiteto (milestone M1)

## Contexto
O motor `tools/ai-team` assumia `main` como base das worktrees e alvo do reconcile.
Neste repo, push na `main` do GitHub **dispara deploy de produção** (Railway + Vercel,
`.github/workflows/deploy-*.yml`) e a operação diária vive na branch
`pilot-safe/p0-blockers-20260424` (135 commits à frente da main em 2026-07-08).
Usar a main localmente criaria risco de deploy acidental de código não validado no piloto.

## Decisão
`.ai-team.json` ganha `baseBranch` (default `"main"` — repos novos não mudam nada).
`worker-runner` cria worktrees a partir dela; `reconciler` exige estar nela pra mergear.
Neste repo: `baseBranch = "pilot-safe/p0-blockers-20260424"`. Junto, o `smoke` do config
passou a `py -3.12 -m pytest saas-backend -q` (o `python` do PATH desta máquina não tem
as dependências do projeto).

## Consequências
- O time multi-agente trabalha e integra sem encostar na main de deploy.
- Promover pra produção continua sendo um ato explícito (merge pilot-safe → main),
  fora do fluxo do reconciler.
- Se a branch vigente mudar, atualizar `baseBranch` no `.ai-team.json` e o RESUME.md.
