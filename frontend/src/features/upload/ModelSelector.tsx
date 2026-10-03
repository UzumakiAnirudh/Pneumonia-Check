import { Columns2, Cpu, Layers } from 'lucide-react';
import type { ModelChoice } from '@/api/types';
import { cn } from '@/utils/cn';

const OPTIONS: { value: ModelChoice; title: string; subtitle: string; icon: typeof Cpu }[] = [
  { value: 'densenet', title: 'DenseNet121', subtitle: 'Convolutional network', icon: Layers },
  { value: 'swin', title: 'Swin Transformer', subtitle: 'Vision transformer', icon: Cpu },
  { value: 'both', title: 'Compare Both', subtitle: 'Run side by side', icon: Columns2 },
];

export function ModelSelector({
  value,
  onChange,
  disabled,
}: {
  value: ModelChoice;
  onChange: (m: ModelChoice) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset disabled={disabled}>
      <legend className="mb-3 text-sm font-semibold">Model</legend>
      <div className="grid gap-2.5 sm:grid-cols-3 lg:grid-cols-1 2xl:grid-cols-3">
        {OPTIONS.map(({ value: v, title, subtitle, icon: Icon }) => {
          const selected = v === value;
          return (
            <label
              key={v}
              className={cn(
                'relative flex cursor-pointer items-center gap-3 rounded-xl border p-3 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent',
                selected
                  ? 'border-primary bg-primary-light'
                  : 'border-border bg-surface hover:bg-surface-2',
              )}
            >
              <input
                type="radio"
                name="model"
                value={v}
                checked={selected}
                onChange={() => onChange(v)}
                className="sr-only"
              />
              <span
                className={cn(
                  'grid h-9 w-9 shrink-0 place-items-center rounded-lg',
                  selected ? 'bg-primary text-white' : 'bg-surface-2 text-ink-muted',
                )}
              >
                <Icon className="h-[18px] w-[18px]" aria-hidden />
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    'block text-sm font-semibold',
                    selected ? 'text-primary-text' : 'text-ink',
                  )}
                >
                  {title}
                </span>
                <span className="block text-xs text-ink-muted">{subtitle}</span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
