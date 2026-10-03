import type { TrainingStatus as Status } from '@/api/types';

export const RUNNING = new Set(['training', 'evaluating', 'comparing']);

export function stateText(t: Status): string {
  if (RUNNING.has(t.state)) return `Training Version 2 · ${Math.round(t.percent)}%`;
  if (t.state === 'activated') return 'Version 2 is active';
  if (t.state === 'kept_previous') return 'Version 1 kept (V2 not better)';
  if (t.state === 'failed') return 'Training stopped';
  return t.label;
}
