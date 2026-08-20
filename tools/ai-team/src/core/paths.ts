import path from 'node:path';
import { MONOREPO_ROOT } from './config.ts';

/** Raiz do monorepo-alvo (detectada via `git rev-parse --show-toplevel`). */
export { MONOREPO_ROOT };
export const SLOTS_DIR = path.join(MONOREPO_ROOT, 'specs', 'slots');
export const WORKTREES_DIR = path.join(MONOREPO_ROOT, '.worktrees');
