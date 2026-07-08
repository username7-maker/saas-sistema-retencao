import { isAvailable, scanSlots } from '../core/slot-scanner.ts';

const C = { reset: '\x1b[0m', dim: '\x1b[2m', green: '\x1b[32m', bold: '\x1b[1m' };

export async function plan(milestone?: string): Promise<void> {
  const slots = await scanSlots(milestone);
  const available = slots.filter(isAvailable);
  console.log(
    `${C.bold}slots disponíveis${milestone ? ` em ${milestone}` : ''}: ${available.length}/${slots.length}${C.reset}\n`,
  );
  for (const s of available) {
    console.log(`  ${C.green}${s.milestone}/${s.id}${C.reset}`);
  }
  if (available.length === 0) {
    console.log(`${C.dim}(nenhum slot livre)${C.reset}`);
  }
  console.log(
    `\n${C.dim}use:${C.reset} ai-team start --slot=<id> --worker=<name>${milestone ? ` --milestone=${milestone}` : ''}`,
  );
}
