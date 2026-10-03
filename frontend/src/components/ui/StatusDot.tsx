import { cn } from '@/utils/cn';

const tones = {
  online: 'bg-normal',
  warning: 'bg-warning',
  offline: 'bg-pneumonia',
  idle: 'bg-ink-muted',
} as const;

export function StatusDot({ status, pulse }: { status: keyof typeof tones; pulse?: boolean }) {
  return (
    <span className="relative inline-flex h-2.5 w-2.5" aria-hidden>
      {pulse && (
        <span className={cn('absolute inset-0 animate-pulse-ring rounded-full', tones[status])} />
      )}
      <span className={cn('relative h-2.5 w-2.5 rounded-full', tones[status])} />
    </span>
  );
}
