import { scanSlots, statusLabel } from './slot-scanner.ts';
import { scanWorkerBranches, indexByKey } from './branch-scanner.ts';
import { listWorktrees } from './git.ts';
import type { Slot, WorkerBranch } from '../types.ts';

const C = {
  reset: '\x1b[0m',
  dim: '\x1b[2m',
  bold: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  red: '\x1b[31m',
};

function statusColor(s: string): string {
  if (s === 'available') return C.dim + s + C.reset;
  if (s.startsWith('claimed')) return C.yellow + s + C.reset;
  if (s.startsWith('done')) return C.green + s + C.reset;
  if (s.startsWith('blocked')) return C.red + s + C.reset;
  return s;
}

/**
 * Combina estado da main + branches worker.
 * Se há branch worker pra esse slot, o estado da branch tem precedência
 * (claimed/done/blocked vivem na branch até serem mergeados).
 */
function effective(
  slot: Slot,
  byKey: Map<string, WorkerBranch>,
): { status: Slot['status']; owner: string | null } {
  const info = byKey.get(`${slot.milestone}/${slot.id}`);
  if (info) return { status: info.status, owner: info.owner ?? slot.owner };
  return { status: slot.status, owner: slot.owner };
}

export async function printDashboard(milestone?: string): Promise<void> {
  const slots = await scanSlots(milestone);
  const branches = await scanWorkerBranches();
  const byKey = indexByKey(branches);
  const wts = await listWorktrees();
  const main = wts.find((w) => w.branch === 'main' || w.branch === '');

  console.log(`${C.bold}━━━ ai-team dashboard ━━━${C.reset}`);
  if (main) console.log(`${C.dim}main: ${main.head} @ ${main.path}${C.reset}`);
  console.log();

  const byMs: Record<string, Slot[]> = {};
  for (const s of slots) (byMs[s.milestone] ??= []).push(s);

  for (const m of Object.keys(byMs).sort()) {
    console.log(`${C.bold}${m}${C.reset}`);
    const counts = { available: 0, claimed: 0, done: 0, blocked: 0, unknown: 0 };
    for (const s of byMs[m]!) {
      const eff = effective(s, byKey);
      const effSlot: Slot = { ...s, status: eff.status, owner: eff.owner };
      const label = statusLabel(effSlot);
      if (label === 'available') counts.available++;
      else if (label.startsWith('claimed')) counts.claimed++;
      else if (label.startsWith('done')) counts.done++;
      else if (label.startsWith('blocked')) counts.blocked++;
      else counts.unknown++;
      const owner = eff.owner ? `${C.dim}(${eff.owner})${C.reset}` : '';
      console.log(`  ${s.id.padEnd(32)} ${statusColor(label).padEnd(40)} ${owner}`);
    }
    console.log(
      `  ${C.dim}─ ${counts.available} available · ${counts.claimed} claimed · ${counts.done} done · ${counts.blocked} blocked${C.reset}`,
    );
    console.log();
  }

  const active = wts.filter((w) => w.branch && w.branch !== 'main');
  if (active.length > 0) {
    console.log(`${C.bold}worktrees ativas${C.reset}`);
    for (const w of active) {
      console.log(`  ${C.cyan}${w.name.padEnd(20)}${C.reset} ${w.branch.padEnd(45)} ${C.dim}${w.head}${C.reset}`);
    }
  } else {
    console.log(`${C.dim}sem worktrees workers ativas${C.reset}`);
  }
}
