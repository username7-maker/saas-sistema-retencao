#!/usr/bin/env node
import { plan } from './cli/plan.ts';
import { start } from './cli/start.ts';
import { status } from './cli/status.ts';
import { reconcile } from './cli/reconcile.ts';
import { auto } from './cli/auto.ts';

function parseArgs(argv: string[]): Record<string, string | boolean> {
  const out: Record<string, string | boolean> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    if (!a.startsWith('--')) continue;
    const eq = a.indexOf('=');
    if (eq !== -1) {
      out[a.slice(2, eq)] = a.slice(eq + 1);
    } else {
      const next = argv[i + 1];
      if (next && !next.startsWith('--')) {
        out[a.slice(2)] = next;
        i++;
      } else {
        out[a.slice(2)] = true;
      }
    }
  }
  return out;
}

function getStr(args: Record<string, string | boolean>, k: string): string | undefined {
  const v = args[k];
  return typeof v === 'string' ? v : undefined;
}

function help(): never {
  console.log(`ai-team — Architect CLI (desenvolvimento multi-agente local)

  ai-team plan [--milestone=M1]
      Lista slots available.

  ai-team start --slot=<id> --worker=<name> [--milestone=M1] [--force]
      Cria worktree em .worktrees/<worker>/, faz claim do slot, imprime prompt
      pra colar no Claude.

  ai-team status [--milestone=M1]
      Dashboard ASCII (slots por status + worktrees ativas).

  ai-team reconcile [--cleanup=false] [--dry-run]
      Merge branches de worker 'done' na main, sincroniza barrels, roda smoke,
      remove worktrees + branches mergeadas.

  ai-team auto [--milestone=M1] [--poll-seconds=15]
      Loop autônomo: dashboard + reconcile automático quando slots 'done' aparecem.
      Não cria workers — só monitora. Ctrl+C pra sair.
`);
  process.exit(0);
}

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);
  switch (cmd) {
    case 'plan':
      return plan(getStr(args, 'milestone'));
    case 'start': {
      const slot = getStr(args, 'slot');
      const worker = getStr(args, 'worker');
      if (!slot || !worker) {
        console.error('uso: ai-team start --slot=<id> --worker=<name> [--milestone=M1]');
        process.exit(2);
      }
      const ms = getStr(args, 'milestone');
      return start({
        slot,
        worker,
        ...(ms ? { milestone: ms } : {}),
        force: args.force === true,
      });
    }
    case 'status':
      return status(getStr(args, 'milestone'));
    case 'reconcile':
      return reconcile({
        cleanup: args.cleanup !== 'false',
        dryRun: args['dry-run'] === true,
      });
    case 'auto': {
      const ms = getStr(args, 'milestone');
      const ps = getStr(args, 'poll-seconds');
      return auto({
        ...(ms ? { milestone: ms } : {}),
        ...(ps ? { pollSeconds: parseInt(ps, 10) } : {}),
      });
    }
    case 'help':
    case '--help':
    case '-h':
    case undefined:
      help();
    default:
      console.error(`comando desconhecido: ${cmd}`);
      help();
  }
}

main().catch((err) => {
  console.error('erro fatal:', err instanceof Error ? err.message : err);
  process.exit(1);
});
