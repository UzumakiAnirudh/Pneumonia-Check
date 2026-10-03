import { cn } from '@/utils/cn';

export function HeatmapLegend({ className }: { className?: string }) {
  return (
    <div
      className={cn('flex items-center gap-2.5 text-[11px] text-slate-400', className)}
      aria-label="Heatmap colour legend: blue is low influence, red is high influence"
    >
      <span>Low</span>
      <span className="bg-jet h-2 w-28 rounded-full sm:w-36" aria-hidden />
      <span>High influence</span>
    </div>
  );
}
