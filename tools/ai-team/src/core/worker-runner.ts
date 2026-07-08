import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WORKTREES_DIR } from './paths.ts';
import { loadConfig } from './config.ts';
import { worktreeAdd, commit } from './git.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROMPT_PATH = path.resolve(__dirname, '../prompts/worker.md');

export interface StartWorkerOpts {
  workerName: string;        // ex: "worker-A"
  slotId: string;            // ex: "tool-parse-datetime"
  milestone: string;         // ex: "M1"
}

export interface StartWorkerResult {
  worktreePath: string;
  branch: string;
  prompt: string;            // pra colar no terminal do Claude
  alreadyExists: boolean;
}

/**
 * Cria worktree + claim do slot + retorna prompt pro humano colar num Claude novo.
 * NÃO faz spawn do Claude — o usuário abre o terminal manualmente em `cd <worktreePath>`.
 */
export async function startWorker(opts: StartWorkerOpts): Promise<StartWorkerResult> {
  const { branchPrefix } = loadConfig();
  const branch = `${branchPrefix}/${opts.milestone}/${opts.slotId}`;
  const wtPath = path.join(WORKTREES_DIR, opts.workerName);

  let alreadyExists = false;
  try {
    await fs.access(wtPath);
    alreadyExists = true;
  } catch {
    /* novo */
  }

  if (!alreadyExists) {
    await worktreeAdd(opts.workerName, branch, 'main');
    // Claim dentro da branch do worker — commitado pra dashboard/reconciler
    // enxergarem via `git show <branch>:specs/slots/.../STATUS.txt`.
    const slotRel = path.join('specs', 'slots', opts.milestone, opts.slotId);
    const slotDir = path.join(wtPath, slotRel);
    await fs.mkdir(slotDir, { recursive: true });
    await fs.writeFile(path.join(slotDir, 'STATUS.txt'), `claimed:${opts.workerName}\n`);
    await fs.writeFile(path.join(slotDir, 'OWNER.txt'), `${opts.workerName}\n`);
    await commit(
      wtPath,
      `claim: ${opts.milestone}/${opts.slotId} by ${opts.workerName}`,
      [`${slotRel}/STATUS.txt`, `${slotRel}/OWNER.txt`],
    );
  }

  const template = await fs.readFile(PROMPT_PATH, 'utf-8');
  const prompt = template
    .replace(/\{\{workerName\}\}/g, opts.workerName)
    .replace(/\{\{slotId\}\}/g, opts.slotId)
    .replace(/\{\{milestone\}\}/g, opts.milestone)
    .replace(/\{\{branch\}\}/g, branch)
    .replace(/\{\{worktreePath\}\}/g, wtPath);

  return { worktreePath: wtPath, branch, prompt, alreadyExists };
}
