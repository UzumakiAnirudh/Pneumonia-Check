import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import { cn } from '@/utils/cn';

export interface SegmentOption<T extends string> {
  value: T;
  label: ReactNode;
  icon?: ReactNode;
  disabled?: boolean;
  description?: string;
}

interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  variant?: 'light' | 'viewer';
  size?: 'sm' | 'md';
  className?: string;
  fullWidth?: boolean;
}

/** Accessible radio-group styled as a segmented control (arrow keys move selection). */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
  variant = 'light',
  size = 'md',
  className,
  fullWidth,
}: SegmentedControlProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.filter((o) => !o.disabled);

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const keys = ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'];
    if (!keys.includes(e.key)) return;
    e.preventDefault();
    const idx = enabled.findIndex((o) => o.value === value);
    let next = idx;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (idx + 1) % enabled.length;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp')
      next = (idx - 1 + enabled.length) % enabled.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = enabled.length - 1;
    const opt = enabled[next];
    onChange(opt.value);
    refs.current[options.indexOf(opt)]?.focus();
  };

  const viewer = variant === 'viewer';
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn(
        'inline-flex gap-1 rounded-xl p-1',
        viewer ? 'border border-viewer-line bg-viewer-panel' : 'border border-border bg-surface-2',
        fullWidth && 'flex w-full',
        className,
      )}
    >
      {options.map((opt, i) => {
        const selected = opt.value === value;
        return (
          <button
            key={opt.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            title={opt.description}
            disabled={opt.disabled}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(opt.value)}
            onKeyDown={onKeyDown}
            className={cn(
              'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-40',
              size === 'sm' ? 'h-7 px-2.5 text-xs' : 'h-9 px-3.5 text-sm',
              fullWidth && 'flex-1',
              viewer
                ? selected
                  ? 'bg-accent/15 text-white shadow-[inset_0_0_0_1px_rgb(var(--accent)/0.6)]'
                  : 'text-slate-400 hover:text-slate-100'
                : selected
                  ? 'bg-surface text-ink shadow-soft'
                  : 'text-ink-muted hover:text-ink',
            )}
          >
            {opt.icon}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
