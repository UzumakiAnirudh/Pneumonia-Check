import { ShieldAlert, ShieldCheck } from 'lucide-react';
import type { Reliability } from '@/api/types';
import { cn } from '@/utils/cn';
import { pct } from '@/utils/format';

export function ReliabilityBadge({
  reliability,
  className,
}: {
  reliability: Reliability;
  className?: string;
}) {
  const high = reliability.level === 'high';
  const Icon = high ? ShieldCheck : ShieldAlert;
  return (
    <div
      role="status"
      className={cn(
        'flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm',
        high
          ? 'border-normal/40 bg-normal/10 text-normal-ink'
          : 'border-warning/50 bg-warning/10 text-warning-ink',
        className,
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div>
        <p className="font-semibold">
          {high ? 'High confidence' : 'Low confidence — recommend expert review'}
        </p>
        <p className="text-xs opacity-90">
          {high ? 'All stages are at or above' : 'At least one stage is below'} the{' '}
          <span className="num">{pct(reliability.threshold, 0)}</span> reliability threshold.
        </p>
      </div>
    </div>
  );
}
