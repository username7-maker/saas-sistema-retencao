import { runGit } from './git.ts';
import { parseStatus } from './slot-scanner.ts';
import { loadConfig } from './config.ts';
import type { WorkerBranch } from '../types.ts';

async function showBranchFile(branch: string, relPath: string): Promise<string | null> {
  try {
    const { stdout } = await runGit(['show', `${branch}:${relPath}`]);
    return stdout;
  } catch {
    return null;
  }
}

/**
 * Lista todas as branches de worker (`<prefix>/*`) e lê STATUS+OWNER de cada uma.
 * Lê dos commits da própria branch (não da working tree), então funciona mesmo
 * sem worktree montada — basta a branch existir.
 */
export async function scanWorkerBranches(): Promise<WorkerBranch[]> {
  const { branchPrefix } = loadConfig();
  const { stdout } = await runGit([
    'for-each-ref',
    '--format=%(refname:short)',
    `refs/heads/${branchPrefix}/`,
  ]);
  const branches = stdout.split('\n').map((l) => l.trim()).filter(Boolean);
  const out: WorkerBranch[] = [];
  for (const branch of branches) {
    // Esperado: <prefix>/<milestone>/<slotId>
    const parts = branch.split('/');
    if (parts.length < 3) continue;
    const milestone = parts[1]!;
    const slotId = parts.slice(2).join('/');
    const slotRel = `specs/slots/${milestone}/${slotId}`;
    const statusRaw = await showBranchFile(branch, `${slotRel}/STATUS.txt`);
    const ownerRaw = await showBranchFile(branch, `${slotRel}/OWNER.txt`);
    const owner = ownerRaw ? ownerRaw.trim() : null;
    out.push({
      branch,
      milestone,
      slotId,
      worker: owner ?? slotId,
      status: statusRaw ? parseStatus(statusRaw) : 'available',
      owner,
    });
  }
  return out;
}

/** Indexa por chave "<milestone>/<slotId>" pra lookup rápido. */
export function indexByKey(infos: WorkerBranch[]): Map<string, WorkerBranch> {
  const m = new Map<string, WorkerBranch>();
  for (const i of infos) m.set(`${i.milestone}/${i.slotId}`, i);
  return m;
}
