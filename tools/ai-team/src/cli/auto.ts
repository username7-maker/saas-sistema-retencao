import { isDone, scanSlots } from '../core/slot-scanner.ts';
import { reconcile } from '../core/reconciler.ts';
import { printDashboard } from '../core/dashboard.ts';

const C = { reset: '\x1b[0m', dim: '\x1b[2m', green: '\x1b[32m', yellow: '\x1b[33m', bold: '\x1b[1m' };

export interface AutoOpts {
  milestone?: string;
  pollSeconds?: number;
  maxIterations?: number;
}

/**
 * Loop autônomo do Architect: monitora slots, dispara reconciler quando ≥1 slot 'done',
 * imprime dashboard a cada poll. Não cria workers — apenas vigia + reconcilia.
 */
export async function auto(opts: AutoOpts = {}): Promise<void> {
  const poll = (opts.pollSeconds ?? 15) * 1000;
  const max = opts.maxIterations ?? 240; // 1h em 15s

  console.log(`${C.bold}━━━ ai-team auto-monitor ━━━${C.reset}`);
  console.log(`${C.dim}poll a cada ${poll / 1000}s, max ${max} iterações. Ctrl+C pra parar.${C.reset}\n`);

  for (let i = 0; i < max; i++) {
    console.log(`${C.dim}── tick ${i + 1}/${max} @ ${new Date().toISOString()} ──${C.reset}`);
    await printDashboard(opts.milestone);

    const slots = await scanSlots(opts.milestone);
    const done = slots.filter(isDone);
    if (done.length > 0) {
      console.log(`\n${C.yellow}${done.length} slot(s) done — disparando reconciler...${C.reset}\n`);
      try {
        const r = await reconcile({ cleanup: true });
        if (r.conflicts.length > 0) {
          console.log(`${C.yellow}reconciler parou em conflito — intervenção humana necessária${C.reset}`);
          process.exit(1);
        }
      } catch (err) {
        console.log(`${C.yellow}reconciler falhou: ${(err as Error).message}${C.reset}`);
      }
    }

    const left = slots.filter(
      (s) => s.status === 'available' || (typeof s.status === 'object' && s.status.kind === 'claimed'),
    );
    if (left.length === 0) {
      console.log(`\n${C.green}✓ nada disponível nem em curso. ai-team auto encerrando.${C.reset}`);
      return;
    }

    await new Promise((r) => setTimeout(r, poll));
  }
  console.log(`${C.yellow}max iterações atingido sem encerrar — saindo${C.reset}`);
}
