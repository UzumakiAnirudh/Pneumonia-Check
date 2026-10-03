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
import type { EpochLog, ModelKey } from '@/api/types';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { ChartTooltip } from './ChartTooltip';

type Metric = 'loss' | 'acc';

/** Loss and accuracy are separate charts (never a dual axis). Solid = train, dashed = validation. */
function CurveChart({
  logs,
  metric,
  height,
}: {
  logs: Partial<Record<ModelKey, EpochLog[]>>;
  metric: Metric;
  height: number;
}) {
  const theme = useChartTheme();
  const models = Object.keys(logs) as ModelKey[];
  const maxEpoch = Math.max(...models.map((m) => logs[m]!.length));
  const data = Array.from({ length: maxEpoch }, (_, i) => {
    const row: Record<string, number> = { epoch: i + 1 };
    for (const m of models) {
      const e = logs[m]![i];
      if (!e) continue;
      row[`${m}_train`] = metric === 'loss' ? e.train_loss : e.train_acc;
      row[`${m}_val`] = metric === 'loss' ? e.val_loss : e.val_acc;
    }
    return row;
  });
  const title = metric === 'loss' ? 'Loss' : 'Accuracy';
  return (
    <figure>
      <figcaption className="mb-1 text-sm font-semibold">{title} vs epoch</figcaption>
      <div
        style={{ height }}
        role="img"
        aria-label={`${title} per epoch for training and validation`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
            <CartesianGrid stroke={theme.grid} vertical={false} />
            <XAxis
              dataKey="epoch"
              tick={{ fill: theme.axis, fontSize: 11 }}
              stroke={theme.grid}
              label={{
                value: 'Epoch',
                position: 'insideBottom',
                offset: -8,
                fill: theme.axis,
                fontSize: 11,
              }}
            />
            <YAxis
              tick={{ fill: theme.axis, fontSize: 11 }}
              stroke={theme.grid}
              width={44}
              domain={metric === 'acc' ? ['auto', 1] : [0, 'auto']}
              tickFormatter={(v: number) =>
                metric === 'acc' ? `${Math.round(v * 100)}%` : v.toFixed(2)
              }
            />
            <Tooltip
              content={
                <ChartTooltip
                  labelFormatter={(l) => `Epoch ${l}`}
                  valueFormatter={(v) =>
                    metric === 'acc' ? `${(v * 100).toFixed(1)}%` : v.toFixed(4)
                  }
                />
              }
              cursor={{ stroke: theme.axis, strokeWidth: 1 }}
            />
            <Legend
              verticalAlign="top"
              height={44}
              iconType="plainline"
              wrapperStyle={{ fontSize: 12 }}
              formatter={(value) => <span style={{ color: theme.text }}>{value}</span>}
            />
            {models.flatMap((m) => [
              <Line
                key={`${m}_train`}
                dataKey={`${m}_train`}
                name={`${MODEL_META[m].short} · train`}
                stroke={theme.series[m]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }}
              />,
              <Line
                key={`${m}_val`}
                dataKey={`${m}_val`}
                name={`${MODEL_META[m].short} · validation`}
                stroke={theme.series[m]}
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={false}
                activeDot={{ r: 4, stroke: theme.surface, strokeWidth: 2 }}
              />,
            ])}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

export function TrainingCurves({ logs }: { logs: Partial<Record<ModelKey, EpochLog[]>> }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <CurveChart logs={logs} metric="loss" height={280} />
      <CurveChart logs={logs} metric="acc" height={280} />
    </div>
  );
}
