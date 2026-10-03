import { motion, useReducedMotion } from 'framer-motion';
import type { AnyLabel, FinalLabel } from '@/api/types';
import { LABELS, TONE_CLASSES } from '@/utils/labels';

const ORDER: AnyLabel[] = ['NORMAL', 'PNEUMONIA', 'BACTERIAL', 'VIRAL'];
import { pct } from '@/utils/format';
import { cn } from '@/utils/cn';

/**
 * Probability breakdown across the final classes (NORMAL/PNEUMONIA when Stage 2 did not run). Plain HTML bars:
 * each row is direct-labelled with class name, icon and value (identity never colour-only).
 */
export function ProbabilityChart({
  probabilities,
  highlight,
  compact = false,
}: {
  probabilities: Partial<Record<AnyLabel, number>>;
  highlight?: FinalLabel | AnyLabel;
  compact?: boolean;
}) {
  const reduce = useReducedMotion();
  return (
    <figure>
      <figcaption className="sr-only">Probability for each class</figcaption>
      <ul className={cn('space-y-2.5', compact && 'space-y-2')}>
        {ORDER.filter((l) => probabilities[l] !== undefined).map((label, i) => {
          const meta = LABELS[label];
          const Icon = meta.icon;
          const value = probabilities[label] ?? 0;
          const active = label === highlight;
          return (
            <li key={label} className="grid grid-cols-[6.5rem_1fr_3.5rem] items-center gap-3">
              <span
                className={cn(
                  'flex items-center gap-1.5 text-sm',
                  active ? 'font-semibold text-ink' : 'text-ink-muted',
                )}
              >
                <Icon className={cn('h-3.5 w-3.5', TONE_CLASSES[meta.tone].text)} aria-hidden />
                {meta.text}
              </span>
              <span
                className="h-2.5 overflow-hidden rounded-full bg-surface-2"
                title={`${meta.text}: ${pct(value)}`}
              >
                <motion.span
                  className={cn(
                    'block h-full rounded-full',
                    TONE_CLASSES[meta.tone].bg,
                    !active && 'opacity-55',
                  )}
                  initial={{ width: reduce ? `${value * 100}%` : 0 }}
                  animate={{ width: `${value * 100}%` }}
                  transition={{
                    duration: reduce ? 0 : 0.8,
                    delay: reduce ? 0 : 0.1 * i,
                    ease: [0.22, 1, 0.36, 1],
                  }}
                />
              </span>
              <span
                className={cn(
                  'num text-right text-sm',
                  active ? 'font-semibold text-ink' : 'text-ink-muted',
                )}
              >
                {pct(value)}
              </span>
            </li>
          );
        })}
      </ul>
    </figure>
  );
}
