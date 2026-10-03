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
import type { ModelKey, RocCurve } from '@/api/types';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { ChartTooltip } from './ChartTooltip';

/** Interpolate each curve onto a shared FPR grid so one crosshair tooltip shows both models. */
function mergeCurves(curves: Partial<Record<ModelKey, RocCurve>>) {
  const grid = Array.from({ length: 101 }, (_, i) => i / 100);
  return grid.map((fpr) => {
    const row: Record<string, number> = { fpr, chance: fpr };
    for (const [m, c] of Object.entries(curves)) {
      if (!c) continue;
      let k = c.fpr.findIndex((x) => x >= fpr);
      if (k === -1) k = c.fpr.length - 1;
      if (k === 0 || c.fpr[k] === fpr) row[m] = c.tpr[k];
      else {
        const t = (fpr - c.fpr[k - 1]) / (c.fpr[k] - c.fpr[k - 1] || 1);
        row[m] = c.tpr[k - 1] + t * (c.tpr[k] - c.tpr[k - 1]);
      }
    }
    return row;
  });
}

export function RocChart({
  curves,
  height = 320,
}: {
  curves: Partial<Record<ModelKey, RocCurve>>;
  height?: number;
}) {
  const theme = useChartTheme();
  const data = mergeCurves(curves);
  const models = Object.keys(curves) as ModelKey[];
  return (
    <figure>
      <div
        style={{ height }}
        role="img"
        aria-label={`ROC curves: ${models.map((m) => `${MODEL_META[m].name} AUC ${curves[m]!.auc.toFixed(3)}`).join(', ')}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 20, left: 4 }}>
            <CartesianGrid stroke={theme.grid} strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="fpr"
              type="number"
              domain={[0, 1]}
              ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
              tick={{ fill: theme.axis, fontSize: 11 }}
              stroke={theme.grid}
              label={{
                value: 'False positive rate (1 − specificity)',
                position: 'insideBottom',
                offset: -12,
                fill: theme.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
              tick={{ fill: theme.axis, fontSize: 11 }}
              stroke={theme.grid}
              width={44}
              label={{
                value: 'True positive rate',
                angle: -90,
                position: 'insideLeft',
                offset: 10,
                fill: theme.axis,
                fontSize: 11,
                dy: 50,
              }}
            />
            <Tooltip
              content={
                <ChartTooltip
                  labelFormatter={(l) => `FPR ${Number(l).toFixed(2)}`}
                  valueFormatter={(v) => `TPR ${v.toFixed(3)}`}
                />
              }
              cursor={{ stroke: theme.axis, strokeWidth: 1 }}
            />
            <Legend
              verticalAlign="top"
              height={28}
              iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: theme.text }}
              formatter={(value) => <span style={{ color: theme.text }}>{value}</span>}
            />
            <Line
              dataKey="chance"
              name="Chance"
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
                name={`${MODEL_META[m].name} (AUC ${curves[m]!.auc.toFixed(3)})`}
                stroke={theme.series[m]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }}
                type="linear"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
