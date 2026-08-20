import fs from 'node:fs/promises';
import path from 'node:path';
import { SLOTS_DIR } from './paths.ts';
import type { Slot, SlotStatus } from '../types.ts';

export function parseStatus(raw: string): SlotStatus {
  const t = raw.trim();
  if (t === 'available') return 'available';
  if (t === 'done') return { kind: 'done' };
  if (t.startsWith('done:')) return { kind: 'done', worker: t.slice(5) };
  if (t.startsWith('claimed:')) return { kind: 'claimed', worker: t.slice(8) };
  if (t === 'blocked') return { kind: 'blocked' };
  if (t.startsWith('blocked:')) return { kind: 'blocked', reason: t.slice(8) };
  return { kind: 'unknown', raw: t };
}

async function readIfExists(p: string): Promise<string | null> {
  try {
    return (await fs.readFile(p, 'utf-8')).trim();
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') return null;
    throw err;
  }
}

async function listMilestones(): Promise<string[]> {
  try {
    const entries = await fs.readdir(SLOTS_DIR);
    const mils: string[] = [];
    for (const e of entries) {
      const p = path.join(SLOTS_DIR, e);
      const s = await fs.stat(p);
      if (s.isDirectory()) mils.push(e);
    }
    return mils.sort();
  } catch {
    return [];
  }
}

export async function scanSlots(milestone?: string): Promise<Slot[]> {
  const milestones = milestone ? [milestone] : await listMilestones();
  const slots: Slot[] = [];
  for (const m of milestones) {
    const dir = path.join(SLOTS_DIR, m);
    let entries: string[] = [];
    try {
      entries = await fs.readdir(dir);
    } catch {
      continue;
    }
    for (const e of entries) {
      if (e.startsWith('_') || e === 'README.md') continue;
      const slotDir = path.join(dir, e);
      const stat = await fs.stat(slotDir);
      if (!stat.isDirectory()) continue;
      const rawStatus = await readIfExists(path.join(slotDir, 'STATUS.txt'));
      const rawOwner = await readIfExists(path.join(slotDir, 'OWNER.txt'));
      slots.push({
        id: e,
        milestone: m,
        path: slotDir,
        status: rawStatus ? parseStatus(rawStatus) : 'available',
        owner: rawOwner,
        hasBrief: !!(await readIfExists(path.join(slotDir, 'BRIEF.md'))),
        hasContract: !!(await readIfExists(path.join(slotDir, 'CONTRACT.md'))),
        hasArtifacts: !!(await readIfExists(path.join(slotDir, 'ARTIFACTS.md'))),
      });
    }
  }
  return slots;
}

export function isAvailable(s: Slot): boolean {
  return s.status === 'available';
}

export function isClaimed(s: Slot): boolean {
  return typeof s.status === 'object' && s.status.kind === 'claimed';
}

export function isDone(s: Slot): boolean {
  return typeof s.status === 'object' && s.status.kind === 'done';
}

export function statusLabel(s: Slot): string {
  if (s.status === 'available') return 'available';
  if (typeof s.status === 'object') {
    if (s.status.kind === 'claimed') return `claimed:${s.status.worker}`;
    if (s.status.kind === 'done') return s.status.worker ? `done:${s.status.worker}` : 'done';
    if (s.status.kind === 'blocked') return s.status.reason ? `blocked:${s.status.reason}` : 'blocked';
    return `unknown:${s.status.raw}`;
  }
  return 'unknown';
}
