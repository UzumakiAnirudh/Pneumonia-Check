import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/utils/cn';
import { TONE_CLASSES, type Tone } from '@/utils/labels';
import { pct } from '@/utils/format';

interface ConfidenceBarProps {
  value: number;
  tone: Tone;
  label: string;
  /** Draws a marker at the reliability threshold. */
  threshold?: number;
  size?: 'sm' | 'md';
  showValue?: boolean;
  className?: string;
}

export function ConfidenceBar({
  value,
  tone,
  label,
  threshold,
  size = 'md',
  showValue = true,
  className,
}: ConfidenceBarProps) {
  const reduce = useReducedMotion();
  const clamped = Math.min(1, Math.max(0, value));
  return (
    <div className={cn('w-full', className)}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-sm text-ink-muted">{label}</span>
        {showValue && (
          <span className={cn('num font-semibold text-ink', size === 'md' ? 'text-xl' : 'text-sm')}>
            {pct(clamped)}
          </span>
        )}
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuetext={pct(clamped)}
        className={cn(
          'relative w-full overflow-hidden rounded-full bg-surface-2',
          size === 'md' ? 'h-3' : 'h-2',
        )}
      >
        <motion.div
          className={cn('h-full rounded-full', TONE_CLASSES[tone].bg)}
          initial={{ width: reduce ? `${clamped * 100}%` : 0 }}
          animate={{ width: `${clamped * 100}%` }}
          transition={{ duration: reduce ? 0 : 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
        {threshold !== undefined && (
          <span
            aria-hidden
            className="absolute inset-y-0 w-0.5 bg-ink/60"
            style={{ left: `${threshold * 100}%` }}
            title={`Threshold ${pct(threshold, 0)}`}
          />
        )}
      </div>
    </div>
  );
}
