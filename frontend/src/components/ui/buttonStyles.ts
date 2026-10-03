import { cn } from '@/utils/cn';

export type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'viewer';
export type Size = 'sm' | 'md' | 'lg';

const base =
  'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50 select-none whitespace-nowrap';

const variants: Record<Variant, string> = {
  primary: 'bg-primary text-white shadow-sm hover:bg-primary/90 active:bg-primary/80',
  secondary: 'bg-primary-light text-primary-text hover:bg-primary-light/70',
  outline: 'border border-border bg-surface text-ink hover:bg-surface-2',
  ghost: 'text-ink-muted hover:bg-surface-2 hover:text-ink',
  danger: 'bg-pneumonia text-white hover:bg-pneumonia/90',
  viewer:
    'border border-viewer-line bg-viewer-panel text-slate-200 hover:bg-viewer-line/60 hover:text-white',
};

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-[15px]',
  lg: 'h-12 px-6 text-base',
};

export function buttonClasses(variant: Variant = 'primary', size: Size = 'md', className?: string) {
  return cn(base, variants[variant], sizes[size], className);
}
