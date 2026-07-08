import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

/**
 * Config opcional do projeto-alvo, lida de `.ai-team.json` na raiz do repo.
 * Tudo tem default sensato — o arquivo só existe quando o projeto quer customizar.
 */
export interface AiTeamConfig {
  /** Comando de smoke rodado pelo reconciler após merge. Default: typecheck recursivo. */
  smoke: string[];
  /** Prefixo das branches de worker. Default: "worker". Branch vira `<prefix>/<milestone>/<slotId>`. */
  branchPrefix: string;
  /**
   * Barrels (index.ts) que o reconciler sincroniza automaticamente: pra cada path,
   * adiciona `import './<arquivo>';` dos .ts irmãos que faltarem. Opt-in — vazio = não mexe.
   */
  syncBarrels: string[];
}

const DEFAULTS: AiTeamConfig = {
  smoke: ['pnpm', '-r', '--if-present', 'typecheck'],
  branchPrefix: 'worker',
  syncBarrels: [],
};

function detectRoot(): string {
  try {
    const top = execFileSync('git', ['rev-parse', '--show-toplevel'], {
      encoding: 'utf-8',
    }).trim();
    if (top) return top;
  } catch {
    /* não é repo git ou git ausente — cai no fallback abaixo */
  }
  // Fallback: assume layout tools/ai-team/src/core/config.ts → 4 níveis acima.
  const dir = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(dir, '../../../..');
}

export const MONOREPO_ROOT = detectRoot();

let cached: AiTeamConfig | null = null;

export function loadConfig(): AiTeamConfig {
  if (cached) return cached;
  const cfgPath = path.join(MONOREPO_ROOT, '.ai-team.json');
  try {
    const raw = fs.readFileSync(cfgPath, 'utf-8');
    const parsed = JSON.parse(raw) as Partial<AiTeamConfig>;
    cached = {
      smoke: Array.isArray(parsed.smoke) && parsed.smoke.length > 0 ? parsed.smoke : DEFAULTS.smoke,
      branchPrefix: typeof parsed.branchPrefix === 'string' && parsed.branchPrefix ? parsed.branchPrefix : DEFAULTS.branchPrefix,
      syncBarrels: Array.isArray(parsed.syncBarrels) ? parsed.syncBarrels : DEFAULTS.syncBarrels,
    };
  } catch {
    cached = { ...DEFAULTS };
  }
  return cached;
}
