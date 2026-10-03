import { Check, Loader2 } from 'lucide-react';
import { ScanLine } from '@/components/viewer/ScanLine';
import { cn } from '@/utils/cn';
import { PROCESSING_STEPS } from './steps';

export function ProcessingSteps({ current }: { current: number }) {
  return (
    <ol className="space-y-1.5" aria-label="Analysis progress">
      {PROCESSING_STEPS.map((step, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li
            key={step}
            aria-current={active ? 'step' : undefined}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
              active && 'bg-accent/10 text-white',
              done && 'text-slate-300',
              !done && !active && 'text-slate-500',
            )}
          >
            <span
              className={cn(
                'grid h-6 w-6 shrink-0 place-items-center rounded-full border text-[11px]',
                done && 'border-accent bg-accent text-viewer',
                active && 'border-accent text-accent',
                !done && !active && 'border-viewer-line',
              )}
              aria-hidden
            >
              {done ? (
                <Check className="h-3.5 w-3.5" strokeWidth={3} />
              ) : active ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                i + 1
              )}
            </span>
            <span>{step}</span>
            <span className="sr-only">
              {done ? '(done)' : active ? '(in progress)' : '(pending)'}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/** The X-ray with an animated scan line while the backend works. */
export function ProcessingImage({ src, alt }: { src: string | null; alt: string }) {
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-xl bg-viewer-panel">
      {src ? (
        <img src={src} alt={alt} className="max-h-full max-w-full object-contain opacity-80" />
      ) : (
        <div className="h-full w-full" />
      )}
      <ScanLine />
    </div>
  );
}
