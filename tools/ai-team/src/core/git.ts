import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import type { Worktree } from '../types.ts';
import { MONOREPO_ROOT, WORKTREES_DIR } from './paths.ts';

const exec = promisify(execFile);

export async function runGit(
  args: string[],
  cwd: string = MONOREPO_ROOT,
): Promise<{ stdout: string; stderr: string }> {
  const { stdout, stderr } = await exec('git', args, { cwd, maxBuffer: 10 * 1024 * 1024 });
  return { stdout, stderr };
}

export async function listWorktrees(): Promise<Worktree[]> {
  const { stdout } = await runGit(['worktree', 'list', '--porcelain']);
  const blocks = stdout.trim().split(/\n\n+/);
  const out: Worktree[] = [];
  for (const b of blocks) {
    const lines = b.split('\n');
    let p = '', branch = '', head = '';
    for (const l of lines) {
      if (l.startsWith('worktree ')) p = l.slice('worktree '.length);
      if (l.startsWith('HEAD ')) head = l.slice('HEAD '.length).slice(0, 7);
      if (l.startsWith('branch ')) branch = l.slice('branch '.length).replace('refs/heads/', '');
    }
    if (!p) continue;
    const name = p.split('/').pop()!;
    out.push({ name, path: p, branch, head });
  }
  return out;
}

export async function worktreeAdd(workerName: string, branch: string, baseBranch = 'main'): Promise<string> {
  const wtPath = `${WORKTREES_DIR}/${workerName}`;
  // Tenta com branch nova; se já existe, anexa.
  try {
    await runGit(['worktree', 'add', '-b', branch, wtPath, baseBranch]);
  } catch {
    await runGit(['worktree', 'add', wtPath, branch]);
  }
  return wtPath;
}

export async function worktreeRemove(workerName: string): Promise<void> {
  const wtPath = `${WORKTREES_DIR}/${workerName}`;
  try {
    await runGit(['worktree', 'remove', wtPath]);
  } catch {
    await runGit(['worktree', 'remove', '--force', wtPath]);
  }
}

export async function branchExists(branch: string): Promise<boolean> {
  try {
    await runGit(['rev-parse', '--verify', branch]);
    return true;
  } catch {
    return false;
  }
}

export async function deleteBranch(branch: string, force = false): Promise<void> {
  await runGit(['branch', force ? '-D' : '-d', branch]);
}

export async function currentBranch(cwd = MONOREPO_ROOT): Promise<string> {
  const { stdout } = await runGit(['branch', '--show-current'], cwd);
  return stdout.trim();
}

export async function commit(cwd: string, message: string, files: string[]): Promise<void> {
  await runGit(['add', ...files], cwd);
  await runGit(['commit', '-m', message], cwd);
}

export async function mergeNoFf(
  branch: string,
  message: string,
  cwd = MONOREPO_ROOT,
): Promise<{ ok: boolean; output: string }> {
  try {
    const { stdout } = await runGit(['merge', '--no-ff', branch, '-m', message], cwd);
    return { ok: true, output: stdout };
  } catch (err: unknown) {
    const e = err as { stdout?: string; stderr?: string; message?: string };
    return { ok: false, output: `${e.stdout ?? ''}\n${e.stderr ?? ''}\n${e.message ?? ''}` };
  }
}
