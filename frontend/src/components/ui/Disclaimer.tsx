import { Info } from 'lucide-react';
import { cn } from '@/utils/cn';

export const DISCLAIMER_TEXT =
  'PneumoScan AI is a decision-support tool for healthcare professionals. It does not provide a diagnosis and must not replace clinical judgement, radiologist review, or laboratory testing.';

export function Disclaimer({
  compact = false,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <aside
      role="note"
      aria-label="Medical disclaimer"
      className={cn(
        'flex items-start gap-2.5 rounded-xl border border-warning/40 bg-warning/10 text-warning-ink',
        compact ? 'px-3 py-2 text-xs' : 'px-4 py-3 text-sm',
        className,
      )}
    >
      <Info className={cn('mt-0.5 shrink-0', compact ? 'h-3.5 w-3.5' : 'h-4 w-4')} aria-hidden />
      <p>
        <strong className="font-semibold">Decision support only — not a diagnosis.</strong>{' '}
        {compact ? 'Always confirm with a qualified clinician.' : DISCLAIMER_TEXT}
      </p>
    </aside>
  );
}
