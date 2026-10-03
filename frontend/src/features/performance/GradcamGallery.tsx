import { useState } from 'react';
import { CheckCircle2, ImageOff, Target, TriangleAlert, XCircle } from 'lucide-react';
import type { GalleryItem } from '@/api/types';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { HeatmapLegend } from '@/components/viewer/HeatmapLegend';
import { LABELS, MODEL_META, TONE_CLASSES } from '@/utils/labels';
import { pct } from '@/utils/format';
import { cn } from '@/utils/cn';

type Category = GalleryItem['category'];

const CATEGORY_META: Record<Category, { label: string; icon: typeof CheckCircle2; tone: string }> =
  {
    correct: { label: 'Correct', icon: CheckCircle2, tone: 'text-normal-ink' },
    misclassified: { label: 'Misclassified', icon: XCircle, tone: 'text-pneumonia-ink' },
    failure: { label: 'Failure cases', icon: TriangleAlert, tone: 'text-warning-ink' },
  };

function LabelText({ label }: { label: string }) {
  const meta = LABELS[label as keyof typeof LABELS];
  if (!meta) return <span>{label}</span>;
  return <span className={cn('font-semibold', TONE_CLASSES[meta.tone].text)}>{meta.text}</span>;
}

export function GradcamGallery({ items }: { items: GalleryItem[] }) {
  const [category, setCategory] = useState<Category>('correct');
  const shown = items.filter((i) => i.category === category);
  const count = (c: Category) => items.filter((i) => i.category === c).length;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <SegmentedControl<Category>
          label="Gallery category"
          value={category}
          onChange={setCategory}
          options={(Object.keys(CATEGORY_META) as Category[]).map((c) => {
            const Icon = CATEGORY_META[c].icon;
            return {
              value: c,
              label: `${CATEGORY_META[c].label} (${count(c)})`,
              icon: <Icon className={cn('h-4 w-4', CATEGORY_META[c].tone)} aria-hidden />,
            };
          })}
        />
        <div className="rounded-lg bg-viewer px-3 py-1.5">
          <HeatmapLegend />
        </div>
      </div>
      {shown.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border py-10 text-sm text-ink-muted">
          <ImageOff className="h-6 w-6" aria-hidden />
          No examples in this category.
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {shown.map((item) => (
            <li
              key={item.image}
              className="overflow-hidden rounded-xl border border-border bg-surface"
            >
              <div className="bg-viewer">
                <img
                  src={item.image}
                  alt={`Grad-CAM overlay, ${item.true_label} case`}
                  className="aspect-[9/10] w-full object-contain"
                  loading="lazy"
                />
              </div>
              <div className="space-y-1.5 p-3.5 text-sm">
                <p className="text-xs font-medium text-ink-muted">{MODEL_META[item.model].name}</p>
                <p>
                  True <LabelText label={item.true_label} /> · Predicted{' '}
                  <LabelText label={item.pred_label} />
                </p>
                <p className="flex flex-wrap gap-x-3 text-xs text-ink-muted">
                  <span>
                    Confidence <span className="num text-ink">{pct(item.confidence)}</span>
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Target className="h-3 w-3" aria-hidden /> In-lung{' '}
                    <span className="num text-ink">{item.lung_attention_pct.toFixed(0)}%</span>
                  </span>
                </p>
                <p className="text-xs text-ink-muted">{item.note}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
