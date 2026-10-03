import type { MetricSummary, ModelKey } from '@/api/types';
import { METRIC_LABELS } from './labels';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { cn } from '@/utils/cn';

const KEYS = Object.keys(METRIC_LABELS) as (keyof MetricSummary)[];

interface MetricCardsProps {
  metrics: Partial<Record<ModelKey, MetricSummary>>;
  /** Optional per-model deltas (e.g. external − internal). */
  deltas?: Partial<Record<ModelKey, Partial<MetricSummary>>>;
}

/** One card per metric, comparing models. Values are text; colour dots only mark identity. */
export function MetricCards({ metrics, deltas }: MetricCardsProps) {
  const { series } = useChartTheme();
  const models = Object.keys(metrics) as ModelKey[];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {KEYS.map((key) => {
        const best = Math.max(...models.map((m) => metrics[m]![key] ?? -1));
        return (
          <div key={key} className="card p-4" title={METRIC_LABELS[key].hint}>
            <p className="text-xs font-medium text-ink-muted">{METRIC_LABELS[key].label}</p>
            <ul className="mt-2.5 space-y-1.5">
              {models.map((m) => {
                const v = metrics[m]![key];
                const d = deltas?.[m]?.[key];
                return (
                  <li key={m} className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-1.5 text-xs text-ink-muted">
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ background: series[m] }}
                        aria-hidden
                      />
                      <span className="truncate">{MODEL_META[m].short}</span>
                    </span>
                    <span className="flex items-baseline gap-1.5">
                      <span
                        className={cn(
                          'num text-[17px] text-ink',
                          models.length > 1 && v === best ? 'font-semibold' : 'font-normal',
                        )}
                      >
                        {v === null ? 'n/a' : (v * 100).toFixed(1)}
                      </span>
                      {typeof d === 'number' && (
                        <span
                          className={cn(
                            'num text-[11px]',
                            d < 0 ? 'text-pneumonia-ink' : 'text-normal-ink',
                          )}
                        >
                          {d > 0 ? '+' : ''}
                          {(d * 100).toFixed(1)}
                        </span>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
