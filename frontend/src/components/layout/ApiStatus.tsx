import { useApiStatus } from './useApiStatus';
import { StatusDot } from '@/components/ui/StatusDot';
import { cn } from '@/utils/cn';

export function ApiStatus({ className }: { className?: string }) {
  const { status, label } = useApiStatus();
  return (
    <div
      className={cn('flex items-center gap-2 text-xs text-ink-muted', className)}
      role="status"
      aria-live="polite"
    >
      <StatusDot status={status} pulse={status === 'online'} />
      <span>{label}</span>
    </div>
  );
}
