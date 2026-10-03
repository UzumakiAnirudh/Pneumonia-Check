import type { TooltipProps } from 'recharts';

/** Shared tooltip: values in ink colours, identity via a coloured key. */
export function ChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
  valueFormatter = (v) => v.toFixed(3),
}: TooltipProps<number, string> & {
  labelFormatter?: (l: number | string) => string;
  valueFormatter?: (v: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lift">
      <p className="mb-1 font-medium text-ink-muted">
        {labelFormatter ? labelFormatter(label) : label}
      </p>
      <ul className="space-y-0.5">
        {payload
          .filter((p) => p.value !== undefined && p.value !== null)
          .map((p) => (
            <li key={String(p.dataKey)} className="flex items-center gap-2">
              <span
                className="h-0.5 w-3 rounded"
                style={{ background: p.color, opacity: p.strokeDasharray ? 0.7 : 1 }}
                aria-hidden
              />
              <span className="text-ink-muted">{p.name}</span>
              <span className="num ml-auto pl-3 font-semibold text-ink">
                {valueFormatter(Number(p.value))}
              </span>
            </li>
          ))}
      </ul>
    </div>
  );
}
