/** Cyan scan line sweeping over the image during analysis. */
export function ScanLine() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <div className="absolute inset-x-0 h-24 -translate-y-full animate-scan">
        <div className="h-full bg-gradient-to-b from-transparent via-accent/10 to-accent/30" />
        <div className="h-[2px] bg-accent shadow-[0_0_16px_4px_rgb(var(--accent)/0.6)]" />
      </div>
      <div className="bg-grid absolute inset-0 opacity-30" />
    </div>
  );
}
