import type { MetricsResponse, ModelKey } from '@/api/types';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { TASK_LABELS } from './labels';

const POPULATIONS = [
  { key: 'pediatric', label: 'Children (Kermany)' },
  { key: 'adult', label: 'Adults (Cohen, Figure1, Shenzhen)' },
] as const;
const COLS = [
  { key: 'accuracy', label: 'Accuracy' },
  { key: 'recall', label: 'Sensitivity' },
  { key: 'specificity', label: 'Specificity' },
  { key: 'roc_auc', label: 'AUC' },
] as const;

const pct = (v: number | null | undefined) =>
  typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : 'n/a';

/** Test-set performance broken down by population, so adult performance is never hidden in an average. */
export function PopulationTable({ data }: { data: NonNullable<MetricsResponse['by_domain']> }) {
  const { series } = useChartTheme();
  const models = Object.keys(data) as ModelKey[];
  const tasks = ['stage1', 'stage2', 'pipeline'].filter((t) => models.some((m) => data[m]?.[t]));
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm">
        <caption className="sr-only">Test-set metrics by population</caption>
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-ink-muted">
            <th scope="col" className="py-2.5 pr-3 font-semibold">
              Population
            </th>
            <th scope="col" className="px-3 py-2.5 font-semibold">
              Model
            </th>
            <th scope="col" className="px-3 py-2.5 text-right font-semibold">
              n
            </th>
            {COLS.map((c) => (
              <th key={c.key} scope="col" className="px-3 py-2.5 text-right font-semibold">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        {tasks.map((task) => (
          <tbody key={task}>
            <tr>
              <th
                colSpan={3 + COLS.length}
                scope="colgroup"
                className="bg-surface-2 px-3 py-2 text-left text-xs font-semibold text-ink"
              >
                {TASK_LABELS[task] ?? task}
              </th>
            </tr>
            {POPULATIONS.flatMap((pop) =>
              models.map((m, i) => {
                const t = data[m]?.[task]?.[pop.key];
                if (!t) return null;
                return (
                  <tr key={`${pop.key}-${m}`} className="border-b border-border/60">
                    <td className="py-2 pl-3 pr-3 text-ink-muted">{i === 0 ? pop.label : ''}</td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ background: series[m] }}
                          aria-hidden
                        />
                        {MODEL_META[m].name}
                      </span>
                    </td>
                    <td className="num px-3 py-2 text-right text-ink-muted">{t.n}</td>
                    {COLS.map((c) => (
                      <td key={c.key} className="num px-3 py-2 text-right text-ink">
                        {pct(t.metrics[c.key])}
                      </td>
                    ))}
                  </tr>
                );
              }),
            )}
          </tbody>
        ))}
      </table>
      <p className="mt-3 text-xs text-ink-muted">
        Adult bacterial pneumonia has few public images, so adult Stage 2 numbers rest on a small
        sample — read them with caution. For the 3-class pipeline, sensitivity/specificity are
        macro-averaged.
      </p>
    </div>
  );
}
