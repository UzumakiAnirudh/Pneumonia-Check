import { useId } from 'react';
import { cn } from '@/utils/cn';

interface LogoMarkProps {
  className?: string;
  /** Animate the scan line (used during analysis / hero). */
  animated?: boolean;
  title?: string;
}

/** Stylised lungs with a cyan scan line passing across. */
export function LogoMark({ className, animated = false, title = 'PneumoScan AI' }: LogoMarkProps) {
  const uid = useId().replace(/:/g, '');
  const scanId = `ps-scan-${uid}`;
  const clipId = `ps-lungs-${uid}`;
  return (
    <svg viewBox="0 0 64 64" className={cn('h-9 w-9', className)} role="img" aria-label={title}>
      <defs>
        <linearGradient id={scanId} x1="0" x2="1">
          <stop offset="0" stopColor="#14B8C4" stopOpacity="0" />
          <stop offset="0.5" stopColor="#14B8C4" />
          <stop offset="1" stopColor="#14B8C4" stopOpacity="0" />
        </linearGradient>
        <clipPath id={clipId}>
          <path d="M28.5 20.5C21 18.5 10.5 28 9 42.5c-.8 8.2 3 13.2 9.5 12.6 6.8-.6 10-5 10-11.6z" />
          <path d="M35.5 20.5C43 18.5 53.5 28 55 42.5c.8 8.2-3 13.2-9.5 12.6-6.8-.6-10-5-10-11.6z" />
        </clipPath>
      </defs>
      {/* trachea + bronchi */}
      <path
        d="M32 6v15m0 0c-1.5 3-4 4.5-6.5 5.5M32 21c1.5 3 4 4.5 6.5 5.5"
        fill="none"
        strokeWidth="3.2"
        strokeLinecap="round"
        className="stroke-primary-text"
      />
      <g clipPath={`url(#${clipId})`}>
        <rect x="0" y="0" width="64" height="64" className="fill-primary-text" />
        <g
          className={
            animated ? 'motion-safe:animate-[ps-sweep_2.4s_ease-in-out_infinite]' : undefined
          }
        >
          <rect x="0" y="36" width="64" height="9" fill="#14B8C4" opacity="0.28" />
        </g>
      </g>
      <g
        className={
          animated ? 'motion-safe:animate-[ps-sweep_2.4s_ease-in-out_infinite]' : undefined
        }
      >
        <rect x="3" y="39.5" width="58" height="2.6" rx="1.3" fill={`url(#${scanId})`} />
      </g>
      <style>{`@keyframes ps-sweep{0%,100%{transform:translateY(-14px)}50%{transform:translateY(10px)}}`}</style>
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <LogoMark />
      <span className="text-[17px] font-semibold tracking-tight text-ink">
        PneumoScan<span className="text-accent"> AI</span>
      </span>
    </span>
  );
}
