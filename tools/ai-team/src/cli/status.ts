import { printDashboard } from '../core/dashboard.ts';

export async function status(milestone?: string): Promise<void> {
  await printDashboard(milestone);
}
