import { Link } from 'react-router-dom';
import { CheckCircle2, Cpu, Loader2, ShieldAlert, XCircle } from 'lucide-react';
import { useHealth } from '@/api/hooks';
import { RUNNING, stateText } from './trainingState';
import { cn } from '@/utils/cn';

/** Compact sidebar indicator; links to Settings for details. */
export function TrainingIndicator({ className }: { className?: string }) {
  const { data } = useHealth();
  const t = data?.training;
  if (!t) return null;
  const running = RUNNING.has(t.state);
  const Icon = running
    ? Loader2
    : t.state === 'activated'
      ? CheckCircle2
      : t.state === 'failed'
        ? XCircle
        : ShieldAlert;
  return (
    <Link
      to="/settings"
      className={cn(
        'block rounded-xl border border-border px-3 py-2 text-xs hover:bg-surface-2',
        className,
      )}
      aria-label={`Model training: ${stateText(t)}. Open details.`}
    >
      <span className="flex items-center gap-1.5 font-medium text-ink">
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            running && 'animate-spin text-accent',
            t.state === 'activated' && 'text-normal-ink',
            t.state === 'failed' && 'text-pneumonia-ink',
          )}
          aria-hidden
        />
        {stateText(t)}
      </span>
      {running && (
        <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-surface-2" aria-hidden>
          <span
            className="block h-full rounded-full bg-accent transition-all"
            style={{ width: `${t.percent}%` }}
          />
        </span>
      )}
    </Link>
  );
}

/** Full panel for the Settings page. */
export function TrainingPanel() {
  const { data } = useHealth();
  const t = data?.training;
  const version = data?.model_version;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <Cpu className="h-4 w-4 text-ink-muted" aria-hidden />
        <span className="text-sm text-ink-muted">Active models:</span>
        <span className="font-medium">{version?.label ?? 'unknown'}</span>
      </div>
      {!t ? (
        <p className="text-sm text-ink-muted">No training run in progress.</p>
      ) : (
        <div className="rounded-xl border border-border p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-semibold">{stateText(t)}</p>
            {RUNNING.has(t.state) && (
              <span className="num text-sm text-ink-muted">{t.percent.toFixed(0)}%</span>
            )}
          </div>
          {RUNNING.has(t.state) && (
            <>
              <div
                className="mt-2 h-2.5 overflow-hidden rounded-full bg-surface-2"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(t.percent)}
                aria-label="Training progress"
              >
                <div
                  className="h-full rounded-full bg-accent transition-all"
                  style={{ width: `${t.percent}%` }}
                />
              </div>
              <p className="mt-2 text-sm text-ink">
                {t.label}
                {t.epoch ? (
                  <span className="text-ink-muted">
                    {' '}
                    · epoch <span className="num">{t.epoch}</span> of{' '}
                    <span className="num">{t.epochs ?? '?'}</span> (may stop early)
                  </span>
                ) : null}
              </p>
              <p className="mt-1 text-xs text-ink-muted">
                {t.description}. When it finishes, Version 2 is compared with Version 1 on the same
                test images and switched on automatically only if it is at least as good.
                Predictions keep working meanwhile.
              </p>
            </>
          )}
          {!RUNNING.has(t.state) && t.message && (
            <p className="mt-1 text-sm text-ink-muted">{t.message}</p>
          )}
          {t.updated_at && (
            <p className="mt-2 text-xs text-ink-muted">
              Updated {new Date(t.updated_at).toLocaleTimeString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
