import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { CalibrationCurve, ModelKey } from '@/api/types';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { ChartTooltip } from './ChartTooltip';

/** Reliability diagram: accuracy per confidence bin vs the perfect-calibration diagonal. */
export function CalibrationChart({
  curves,
}: {
  curves: Partial<Record<ModelKey, CalibrationCurve>>;
}) {
  const theme = useChartTheme();
  const models = (Object.keys(curves) as ModelKey[]).filter(
    (m) => curves[m]?.bin_confidence.length,
  );
  const binKeys = Array.from(
    new Set(models.flatMap((m) => curves[m]!.bin_confidence.map((c) => Math.round(c * 100) / 100))),
  ).sort((a, b) => a - b);
  const data = [0, ...binKeys, 1].map((x) => {
    const row: Record<string, number> = { conf: x, ideal: x };
    for (const m of models) {
      const c = curves[m]!;
      const idx = c.bin_confidence.findIndex((v) => Math.round(v * 100) / 100 === x);
      if (idx >= 0) row[m] = c.bin_accuracy[idx];
    }
    return row;
  });

  return (
    <figure>
      <div
        className="h-[260px]"
        role="img"
        aria-label="Reliability diagram: observed accuracy versus predicted confidence"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis
              dataKey="conf"
              type="number"
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              tick={{ fill: theme.axis, fontSize: 11 }}
              stroke={theme.grid}
              label={{
                value: 'Predicted confidence',
                position: 'insideBottom',
                offset: -8,
                fill: theme.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              tick={{ fill: theme.axis, fontSize: 11 }}
              stroke={theme.grid}
              width={40}
            />
            <Tooltip
              content={
                <ChartTooltip
                  labelFormatter={(l) => `Confidence ${Number(l).toFixed(2)}`}
                  valueFormatter={(v) => `${(v * 100).toFixed(1)}%`}
                />
              }
              cursor={{ stroke: theme.axis, strokeWidth: 1 }}
            />
            <Legend
              verticalAlign="top"
              height={28}
              iconType="plainline"
              wrapperStyle={{ fontSize: 12 }}
              formatter={(v) => <span style={{ color: theme.text }}>{v}</span>}
            />
            <Line
              dataKey="ideal"
              name="Perfect calibration"
              stroke={theme.chance}
              strokeDasharray="4 4"
              strokeWidth={1}
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
            {models.map((m) => (
              <Line
                key={m}
                dataKey={m}
                name={MODEL_META[m].name}
                stroke={theme.series[m]}
                strokeWidth={2}
                connectNulls
                dot={{ r: 4, fill: theme.series[m], stroke: theme.surface, strokeWidth: 2 }}
                activeDot={{ r: 5, stroke: theme.surface, strokeWidth: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-muted">
        {models.map((m) => (
          <span key={m}>
            {MODEL_META[m].short} ECE:{' '}
            {curves[m]!.ece_before !== null && (
              <>
                <span className="num text-ink">{curves[m]!.ece_before!.toFixed(3)}</span> before
                →{' '}
              </>
            )}
            <span className="num font-semibold text-ink">
              {curves[m]!.ece_after?.toFixed(3) ?? '—'}
            </span>{' '}
            after temperature scaling
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
