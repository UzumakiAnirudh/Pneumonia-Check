import { motion } from 'framer-motion';
import type { AnyLabel } from '@/api/types';
import { LABELS, TONE_CLASSES } from '@/utils/labels';
import { cn } from '@/utils/cn';

interface PredictionLabelProps {
  label: AnyLabel;
  stage: string;
  size?: 'lg' | 'md' | 'sm';
  className?: string;
}

/** Large result label: icon + text + colour (never colour alone). */
export function PredictionLabel({ label, stage, size = 'lg', className }: PredictionLabelProps) {
  const meta = LABELS[label];
  const Icon = meta.icon;
  const tone = TONE_CLASSES[meta.tone];
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className={cn('flex items-center gap-3', className)}
    >
      <span
        className={cn(
          'grid shrink-0 place-items-center rounded-2xl border',
          tone.soft,
          tone.border,
          tone.text,
          size === 'lg' ? 'h-14 w-14' : size === 'md' ? 'h-11 w-11' : 'h-9 w-9',
        )}
        aria-hidden
      >
        <Icon
          className={size === 'lg' ? 'h-7 w-7' : size === 'md' ? 'h-5 w-5' : 'h-4 w-4'}
          strokeWidth={2.2}
        />
      </span>
      <div className="min-w-0">
        <p className="eyebrow">{stage}</p>
        <p
          className={cn(
            'font-bold tracking-tight',
            tone.text,
            size === 'lg'
              ? 'text-[34px] leading-tight sm:text-label'
              : size === 'md'
                ? 'text-2xl'
                : 'text-lg',
          )}
          data-testid="prediction-label"
        >
          {meta.short}
        </p>
      </div>
    </motion.div>
  );
}
