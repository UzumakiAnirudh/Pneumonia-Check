import type { MetricSummary, ModelKey, ModelTaskMetrics } from '@/api/types';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { cn } from '@/utils/cn';
import { METRIC_LABELS, TASK_LABELS } from './labels';

/** DenseNet121 vs Swin, every metric for every task. Also serves as the table view of the cards. */
export function ComparisonTable({
  internal,
}: {
  internal: Partial<Record<ModelKey, ModelTaskMetrics>>;
}) {
  const { series } = useChartTheme();
  const models = Object.keys(internal) as ModelKey[];
  const tasks = Object.keys(TASK_LABELS).filter((t) =>
    models.some((m) => internal[m]?.[t as keyof ModelTaskMetrics]),
  );
  const keys = Object.keys(METRIC_LABELS) as (keyof MetricSummary)[];
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-sm">
        <caption className="sr-only">
          DenseNet121 versus Swin Transformer on the internal test set
        </caption>
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-ink-muted">
            <th scope="col" className="py-2.5 pr-4 font-semibold">
              Metric
            </th>
            {models.map((m) => (
              <th key={m} scope="col" className="px-3 py-2.5 text-right font-semibold">
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: series[m] }}
                    aria-hidden
                  />
                  {MODEL_META[m].name}
                </span>
              </th>
            ))}
            {models.length === 2 && (
              <th scope="col" className="py-2.5 pl-3 text-right font-semibold">
                Δ (Swin − DenseNet)
              </th>
            )}
          </tr>
        </thead>
        {tasks.map((task) => (
          <tbody key={task}>
            <tr>
              <th
                colSpan={models.length + 2}
                scope="colgroup"
                className="bg-surface-2 px-3 py-2 text-left text-xs font-semibold text-ink"
              >
                {TASK_LABELS[task]}
              </th>
            </tr>
            {keys.map((k) => {
              const vals = models.map(
                (m) => internal[m]?.[task as keyof ModelTaskMetrics]?.metrics[k],
              );
              const best = Math.max(...vals.filter((v): v is number => typeof v === 'number'));
              const delta =
                vals.length === 2 && typeof vals[0] === 'number' && typeof vals[1] === 'number'
                  ? vals[1] - vals[0]
                  : null;
              return (
                <tr key={k} className="border-b border-border/60">
                  <th scope="row" className="py-2 pl-3 pr-4 text-left font-normal text-ink-muted">
                    {METRIC_LABELS[k].label}
                  </th>
                  {vals.map((v, i) => (
                    <td
                      key={models[i]}
                      className={cn(
                        'num px-3 py-2 text-right',
                        v === best && models.length > 1 ? 'font-semibold text-ink' : 'text-ink',
                      )}
                    >
                      {typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : 'n/a'}
                    </td>
                  ))}
                  {models.length === 2 && (
                    <td className="num py-2 pl-3 text-right text-ink-muted">
                      {delta === null
                        ? '—'
                        : `${delta >= 0 ? '+' : '−'}${Math.abs(delta * 100).toFixed(1)}`}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        ))}
      </table>
    </div>
  );
}
