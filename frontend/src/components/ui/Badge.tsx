import type { ReactNode } from 'react';
import { cn } from '@/utils/cn';
import { TONE_CLASSES, type Tone } from '@/utils/labels';

interface BadgeProps {
  tone?: Tone | 'neutral' | 'primary' | 'accent';
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  size?: 'sm' | 'md';
}

export function Badge({ tone = 'neutral', icon, children, className, size = 'sm' }: BadgeProps) {
  const toneClass =
    tone === 'neutral'
      ? 'bg-surface-2 text-ink-muted border-border'
      : tone === 'primary'
        ? 'bg-primary-light text-primary-text border-primary/20'
        : tone === 'accent'
          ? 'bg-accent/10 text-ink border-accent/40'
          : cn(TONE_CLASSES[tone].soft, TONE_CLASSES[tone].text, TONE_CLASSES[tone].border);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        size === 'sm' ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        toneClass,
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
