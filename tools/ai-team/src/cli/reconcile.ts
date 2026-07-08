import { reconcile as runReconcile, type ReconcileOptions } from '../core/reconciler.ts';

const C = { reset: '\x1b[0m', dim: '\x1b[2m', green: '\x1b[32m', red: '\x1b[31m', yellow: '\x1b[33m', bold: '\x1b[1m' };

export async function reconcile(opts: ReconcileOptions): Promise<void> {
  console.log(`${C.bold}━━━ reconciler ━━━${C.reset}\n`);
  const r = await runReconcile(opts);
  const mergedIds = r.mergedSlots.map((s) => s.id);
  console.log();
  console.log(`${C.bold}resumo${C.reset}`);
  console.log(`  merged: ${C.green}${mergedIds.length}${C.reset} (${mergedIds.join(', ') || '—'})`);
  console.log(`  conflitos: ${r.conflicts.length > 0 ? C.red + r.conflicts.length + C.reset : C.dim + '0' + C.reset}`);
  if (mergedIds.length === 0 && r.conflicts.length === 0) {
    return;
  }
  console.log(`  smoke: ${r.smokeOk ? C.green + 'ok' + C.reset : C.red + 'falhou' + C.reset}`);
  if (r.conflicts.length > 0) {
    console.log(`\n${C.yellow}conflitos pra resolver manualmente:${C.reset}`);
    for (const c of r.conflicts) {
      console.log(`  ${c.slot}`);
      console.log(c.output.slice(-500));
    }
    process.exit(1);
  }
  if (!r.smokeOk) process.exit(2);
}
