import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Eye, Lock, ScanSearch } from 'lucide-react';
import { Logo, LogoMark } from '@/components/brand/Logo';
import { ScanLine } from '@/components/viewer/ScanLine';
import { Disclaimer } from '@/components/ui/Disclaimer';

const POINTS = [
  { icon: ScanSearch, text: 'Two-stage detection: Normal vs Pneumonia, then Bacterial vs Viral' },
  { icon: Eye, text: 'Grad-CAM heatmaps show which lung regions drove each prediction' },
  { icon: Lock, text: 'Your analysis history is private to your account' },
];

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="grid min-h-screen bg-bg lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      {/* Brand panel */}
      <aside className="relative hidden overflow-hidden bg-viewer text-slate-200 lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="bg-grid pointer-events-none absolute inset-0 opacity-50" aria-hidden />
        <ScanLine />
        <Link
          to="/"
          className="relative inline-flex items-center gap-3"
          aria-label="PneumoScan AI home"
        >
          <LogoMark className="h-11 w-11" animated />
          <span className="text-xl font-semibold text-white">
            PneumoScan<span className="text-accent"> AI</span>
          </span>
        </Link>
        <div className="relative max-w-md">
          <h2 className="text-[32px] font-bold leading-tight text-white">
            Explainable AI for <span className="text-accent">pneumonia detection</span>
          </h2>
          <ul className="mt-8 space-y-4">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-viewer-line bg-viewer-panel text-accent">
                  <Icon className="h-[18px] w-[18px]" aria-hidden />
                </span>
                <span className="pt-1.5 text-[15px] text-slate-300">{text}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-slate-500">
          Decision support for healthcare professionals — not a diagnosis.
        </p>
      </aside>

      {/* Form */}
      <main className="flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <Link to="/" className="lg:invisible" aria-label="PneumoScan AI home">
            <Logo />
          </Link>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden /> Back to home
          </Link>
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <h1 className="text-[28px] font-bold leading-tight">{title}</h1>
          <p className="mt-2 text-ink-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
        <Disclaimer compact className="mx-auto w-full max-w-md" />
      </main>
    </div>
  );
}
