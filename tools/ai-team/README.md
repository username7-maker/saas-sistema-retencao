# ai-team CLI

Architect CLI que orquestra **workers em git worktrees** com slots + zoning rígido.
É o motor do desenvolvimento multi-agente local: vários Claudes trabalham em paralelo,
cada um numa worktree isolada, sem merge hell.

> Versão generalizada do `apps/ai-team` do projeto `growth-ai-agents`. Funciona em
> **qualquer** monorepo — detecta a raiz via `git rev-parse --show-toplevel`.

## Como roda

```bash
# da raiz do projeto-alvo (instalado em tools/ai-team ou via pnpm --filter)
pnpm --filter @a360/ai-team cli <comando>
# ou, se o bin estiver no PATH:
ai-team <comando>
```

## Comandos

| Comando | O que faz |
|---|---|
| `ai-team plan [--milestone=M1]` | Lista slots `available`. |
| `ai-team start --slot=<id> --worker=<name> [--milestone=M1]` | Cria worktree em `.worktrees/<worker>/`, faz claim do slot, imprime o prompt pra colar num Claude novo. |
| `ai-team status [--milestone=M1]` | Dashboard ASCII (slots por status + worktrees ativas). |
| `ai-team reconcile [--cleanup=false] [--dry-run]` | Merge das branches `done` na main, sincroniza barrels, roda smoke, limpa worktrees. |
| `ai-team auto [--milestone=M1] [--poll-seconds=15]` | Loop autônomo: monitora + reconcilia sozinho. Ctrl+C pra sair. |

## Anatomia de um slot

`specs/slots/<milestone>/<slot-id>/`

```
BRIEF.md        # o quê + critérios de aceite + território (Arquiteto escreve)
DESIGN-SPEC.md  # como: schemas Zod, signatures, nomes exatos (Arquiteto escreve)
CONTRACT.md     # I/O formal + comando de smoke
STATUS.txt      # available | claimed:<worker> | done | blocked:<motivo>
OWNER.txt       # <worker-name>
ARTIFACTS.md    # worker escreve no fim: arquivos tocados + smoke + notas
```

## Config opcional — `.ai-team.json` na raiz

Tudo tem default sensato. Crie o arquivo só pra customizar:

```json
{
  "smoke": ["pnpm", "-r", "--if-present", "typecheck"],
  "branchPrefix": "worker",
  "syncBarrels": ["packages/core/src/tools/library/index.ts"]
}
```

- **smoke** — comando rodado pelo reconciler após merge (default: typecheck recursivo).
- **branchPrefix** — prefixo das branches de worker; vira `<prefix>/<milestone>/<slot>`.
- **syncBarrels** — barrels (index.ts) que o reconciler auto-sincroniza (opt-in).

## Ciclo de vida

```
available ──claim──> claimed:<worker> ──smoke ok──> done ──reconcile──> main (mergeado)
                                          │
                                          └──trava──> blocked:<motivo> (humano/Arquiteto resolve)
```
