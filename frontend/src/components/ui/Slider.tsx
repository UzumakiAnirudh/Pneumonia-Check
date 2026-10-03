import { useId } from 'react';
import { cn } from '@/utils/cn';

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  format?: (value: number) => string;
  variant?: 'light' | 'viewer';
  className?: string;
  hideLabel?: boolean;
}

export function Slider({
  label,
  value,
  min,
  max,
  step = 0.01,
  onChange,
  format = (v) => v.toFixed(2),
  variant = 'light',
  className,
  hideLabel,
}: SliderProps) {
  const id = useId();
  const pctFill = ((value - min) / (max - min)) * 100;
  const viewer = variant === 'viewer';
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <label
        htmlFor={id}
        className={cn(
          'shrink-0 text-xs font-medium',
          viewer ? 'text-slate-400' : 'text-ink-muted',
          hideLabel && 'sr-only',
        )}
      >
        {label}
      </label>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-valuetext={format(value)}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full accent-accent"
        style={{
          background: `linear-gradient(90deg, rgb(var(--accent)) ${pctFill}%, ${
            viewer ? 'rgb(var(--viewer-line))' : 'rgb(var(--border))'
          } ${pctFill}%)`,
        }}
      />
      <span
        className={cn(
          'num w-12 shrink-0 text-right text-xs',
          viewer ? 'text-slate-300' : 'text-ink',
        )}
      >
        {format(value)}
      </span>
    </div>
  );
}
