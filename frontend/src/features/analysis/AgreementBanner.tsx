import { CheckCheck, GitCompareArrows } from 'lucide-react';
import type { Agreement } from '@/api/types';
import { LABELS, MODEL_META } from '@/utils/labels';
import { cn } from '@/utils/cn';

export function AgreementBanner({ agreement }: { agreement: Agreement }) {
  const Icon = agreement.agree ? CheckCheck : GitCompareArrows;
  return (
    <div
      role="status"
      className={cn(
        'flex flex-wrap items-center gap-x-4 gap-y-2 rounded-card border px-5 py-4',
        agreement.agree ? 'border-normal/40 bg-normal/10' : 'border-warning/50 bg-warning/10',
      )}
    >
      <span
        className={cn(
          'grid h-10 w-10 place-items-center rounded-xl',
          agreement.agree ? 'bg-normal/15 text-normal-ink' : 'bg-warning/20 text-warning-ink',
        )}
      >
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'text-lg font-semibold',
            agreement.agree ? 'text-normal-ink' : 'text-warning-ink',
          )}
        >
          {agreement.agree ? 'Both models agree' : 'Models disagree — expert review recommended'}
        </p>
        <p className="text-sm text-ink-muted">
          {Object.entries(agreement.labels)
            .map(([m, l]) => `${MODEL_META[m as keyof typeof MODEL_META].name}: ${LABELS[l].text}`)
            .join('  ·  ')}
        </p>
      </div>
    </div>
  );
}
