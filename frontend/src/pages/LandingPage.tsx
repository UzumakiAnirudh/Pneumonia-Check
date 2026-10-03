import { motion } from 'framer-motion';
import {
  ArrowRight,
  BarChart3,
  Brain,
  Eye,
  FileCheck2,
  ScanSearch,
  ShieldCheck,
  Upload,
  Bug,
  Virus,
  type LucideIcon,
} from 'lucide-react';
import { LogoMark } from '@/components/brand/Logo';
import { ButtonLink } from '@/components/ui/Button';
import { Disclaimer } from '@/components/ui/Disclaimer';
import { ScanLine } from '@/components/viewer/ScanLine';

const FEATURES: { icon: LucideIcon; title: string; body: string; accent: string }[] = [
  {
    icon: ScanSearch,
    title: 'Pneumonia detection',
    body: 'Stage 1 separates normal chest X-rays from pneumonia using DenseNet121 or a Swin Transformer, with calibrated confidence scores.',
    accent: 'text-pneumonia-ink bg-pneumonia/10',
  },
  {
    icon: Brain,
    title: 'Viral vs bacterial',
    body: 'Stage 2 runs only when pneumonia is detected and estimates whether the pattern looks bacterial or viral — flagged as lower certainty.',
    accent: 'text-viral-ink bg-viral/10',
  },
  {
    icon: Eye,
    title: 'Visual explanation',
    body: 'Grad-CAM heatmaps show which lung regions influenced the prediction, with a plain-language summary and a lung-attention check.',
    accent: 'text-primary-text bg-primary-light',
  },
];

const STEPS: { icon: LucideIcon; title: string; body: string }[] = [
  { icon: Upload, title: 'Upload', body: 'PNG, JPEG or DICOM chest X-ray' },
  { icon: FileCheck2, title: 'Validate', body: 'Checks the image is a frontal CXR' },
  { icon: Brain, title: 'Analyze', body: 'Two-stage deep learning classification' },
  { icon: Eye, title: 'Explain', body: 'Grad-CAM heatmap and summary' },
];

function HeroVisual() {
  return (
    <div className="viewer-panel relative aspect-[4/3.4] w-full overflow-hidden p-3 shadow-lift">
      <div className="relative h-full overflow-hidden rounded-xl bg-viewer-panel">
        {/* Abstract CXR silhouette — decorative */}
        <svg viewBox="0 0 400 340" className="absolute inset-0 h-full w-full" aria-hidden>
          <defs>
            <radialGradient id="hero-body" cx="50%" cy="45%" r="60%">
              <stop offset="0" stopColor="#3a4660" />
              <stop offset="1" stopColor="#111A2E" />
            </radialGradient>
            <radialGradient id="hero-heat" cx="34%" cy="66%" r="22%">
              <stop offset="0" stopColor="#ff3b2f" stopOpacity="0.85" />
              <stop offset="0.45" stopColor="#ffd400" stopOpacity="0.55" />
              <stop offset="1" stopColor="#14B8C4" stopOpacity="0" />
            </radialGradient>
          </defs>
          <ellipse cx="200" cy="185" rx="165" ry="150" fill="url(#hero-body)" />
          <path
            d="M188 70c-40-6-95 40-102 120-4 50 14 82 50 80 34-2 52-28 52-66z"
            fill="#0d1424"
            opacity="0.92"
          />
          <path
            d="M212 70c40-6 95 40 102 120 4 50-14 82-50 80-34-2-52-28-52-66z"
            fill="#0d1424"
            opacity="0.92"
          />
          {Array.from({ length: 7 }).map((_, i) => (
            <g key={i} stroke="#9fb0cc" strokeOpacity="0.16" strokeWidth="5" fill="none">
              <path d={`M190 ${92 + i * 26}c-30 -8 -70 0 -98 ${22 + i * 2}`} />
              <path d={`M210 ${92 + i * 26}c30 -8 70 0 98 ${22 + i * 2}`} />
            </g>
          ))}
          <path d="M200 60v210" stroke="#c9d4e6" strokeOpacity="0.25" strokeWidth="18" />
          <ellipse cx="230" cy="205" rx="48" ry="58" fill="#c9d4e6" opacity="0.13" />
          <ellipse
            cx="136"
            cy="225"
            rx="95"
            ry="80"
            fill="url(#hero-heat)"
            className="motion-safe:animate-pulse"
          />
        </svg>
        <ScanLine />
        <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between rounded-xl border border-viewer-line bg-viewer/80 px-3 py-2 backdrop-blur">
          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span className="h-2 w-2 rounded-full bg-pneumonia" aria-hidden />
            <span className="font-semibold text-white">PNEUMONIA</span>
            <span className="text-slate-500">·</span>
            <Bug className="h-3.5 w-3.5 text-bacterial" aria-hidden />
            <span>Bacterial</span>
          </div>
          <span className="num text-xs text-accent">illustration</span>
        </div>
      </div>
    </div>
  );
}

export function LandingPage() {
  return (
    <div className="space-y-16 pb-8">
      <section className="grid items-center gap-10 pt-2 lg:grid-cols-[1.05fr_1fr] lg:gap-14 lg:pt-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div className="mb-6 inline-flex items-center gap-2.5 rounded-full border border-border bg-surface py-1 pl-1 pr-3.5 shadow-soft">
            <LogoMark className="h-7 w-7" animated />
            <span className="text-sm font-medium text-ink-muted">
              PneumoScan AI · Clinical decision support
            </span>
          </div>
          <h1 className="text-[34px] font-bold leading-[1.1] tracking-tight sm:text-[44px]">
            Explainable AI for <span className="text-primary-text">Pneumonia Detection</span>
          </h1>
          <p className="mt-5 max-w-xl text-[17px] leading-relaxed text-ink-muted">
            Upload a chest X-ray to screen for pneumonia, estimate whether it looks viral or
            bacterial, and see exactly which lung regions drove the model's decision — with
            calibrated confidence and a clear flag when expert review is needed.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/analyze" size="lg" icon={<ScanSearch className="h-5 w-5" />}>
              Start Analysis
            </ButtonLink>
            <ButtonLink
              to="/performance"
              size="lg"
              variant="outline"
              icon={<BarChart3 className="h-5 w-5" />}
            >
              Model performance
            </ButtonLink>
          </div>
          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-muted">
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-normal" aria-hidden /> Images processed in memory
            </span>
            <span className="inline-flex items-center gap-2">
              <Virus className="h-4 w-4 text-viral" aria-hidden /> Two-stage hierarchy
            </span>
            <span className="inline-flex items-center gap-2">
              <Eye className="h-4 w-4 text-accent" aria-hidden /> Grad-CAM for CNN &amp; Transformer
            </span>
          </div>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mx-auto w-full max-w-lg"
        >
          <HeroVisual />
        </motion.div>
      </section>

      <section aria-labelledby="features-title">
        <h2 id="features-title" className="sr-only">
          Features
        </h2>
        <div className="grid gap-5 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body, accent }, i) => (
            <motion.article
              key={title}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.4, delay: i * 0.08 }}
              className="card p-6"
            >
              <span className={`mb-4 grid h-11 w-11 place-items-center rounded-xl ${accent}`}>
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-ink-muted">{body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section aria-labelledby="how-title" className="card overflow-hidden p-6 sm:p-8">
        <p className="eyebrow mb-1">Workflow</p>
        <h2 id="how-title" className="text-2xl font-bold">
          How it works
        </h2>
        <ol className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, body }, i) => (
            <li
              key={title}
              className="relative flex items-start gap-3.5 rounded-xl bg-surface-2 p-4"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-white">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <p className="num text-xs text-ink-muted">Step {i + 1}</p>
                <p className="font-semibold">{title}</p>
                <p className="text-sm text-ink-muted">{body}</p>
              </div>
              {i < STEPS.length - 1 && (
                <ArrowRight
                  className="absolute -right-3.5 top-1/2 hidden h-5 w-5 -translate-y-1/2 text-accent lg:block"
                  aria-hidden
                />
              )}
            </li>
          ))}
        </ol>
      </section>

      <Disclaimer />
    </div>
  );
}
