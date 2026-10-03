import { useState } from 'react';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { LABELS } from '@/utils/labels';
import { cn } from '@/utils/cn';

const labelText = (l: string) => LABELS[l as keyof typeof LABELS]?.text ?? l;

/**
 * Interactive confusion matrix. Cell shade = row-normalised rate on one hue (sequential);
 * the number is always printed, so colour is never the only carrier.
 */
export function ConfusionMatrix({
  matrix,
  labels,
  title,
}: {
  matrix: number[][];
  labels: string[];
  title: string;
}) {
  const [mode, setMode] = useState<'count' | 'rate'>('count');
  const [hover, setHover] = useState<[number, number] | null>(null);
  const rowSums = matrix.map((r) => r.reduce((a, b) => a + b, 0) || 1);
  const total = rowSums.reduce((a, b) => a + b, 0);

  const cellText = (i: number, j: number) => {
    const n = matrix[i][j];
    return mode === 'count' ? String(n) : `${((n / rowSums[i]) * 100).toFixed(1)}%`;
  };

  return (
    <figure className="min-w-0">
      <div className="mb-3 flex items-center justify-between gap-2">
        <figcaption className="text-sm font-semibold">{title}</figcaption>
        <SegmentedControl
          label={`${title} display`}
          size="sm"
          value={mode}
          onChange={setMode}
          options={[
            { value: 'count', label: 'Count' },
            { value: 'rate', label: 'Row %' },
          ]}
        />
      </div>
      <div className="flex">
        <div className="flex w-6 items-center justify-center">
          <span className="-rotate-90 whitespace-nowrap text-[11px] font-medium text-ink-muted">
            True label
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <table className="w-full table-fixed border-separate border-spacing-0.5 text-center">
            <thead>
              <tr>
                <th className="w-24" />
                {labels.map((l) => (
                  <th key={l} scope="col" className="pb-1 text-[11px] font-medium text-ink-muted">
                    {labelText(l)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row, i) => (
                <tr key={labels[i]}>
                  <th
                    scope="row"
                    className="pr-2 text-right text-[11px] font-medium text-ink-muted"
                  >
                    {labelText(labels[i])}
                  </th>
                  {row.map((n, j) => {
                    const rate = n / rowSums[i];
                    const strong = rate > 0.55;
                    const isHover = hover?.[0] === i && hover?.[1] === j;
                    return (
                      <td
                        key={j}
                        tabIndex={0}
                        onMouseEnter={() => setHover([i, j])}
                        onMouseLeave={() => setHover(null)}
                        onFocus={() => setHover([i, j])}
                        onBlur={() => setHover(null)}
                        aria-label={`True ${labelText(labels[i])}, predicted ${labelText(labels[j])}: ${n} (${(rate * 100).toFixed(1)}% of row)`}
                        className={cn(
                          'relative h-16 rounded-lg transition-shadow',
                          isHover && 'ring-2 ring-accent',
                        )}
                        style={{ background: `rgb(var(--primary) / ${0.06 + rate * 0.84})` }}
                      >
                        <span
                          className={cn(
                            'num text-[15px] font-semibold',
                            strong ? 'text-white' : 'text-ink',
                          )}
                        >
                          {cellText(i, j)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-center text-[11px] font-medium text-ink-muted">Predicted label</p>
        </div>
      </div>
      <p className="mt-2 h-4 text-xs text-ink-muted" aria-live="polite">
        {hover
          ? `True ${labelText(labels[hover[0]])} → predicted ${labelText(labels[hover[1]])}: ${matrix[hover[0]][hover[1]]} images (${(
              (matrix[hover[0]][hover[1]] / rowSums[hover[0]]) *
              100
            ).toFixed(1)}% of row)`
          : `n = ${total}`}
      </p>
    </figure>
  );
}
