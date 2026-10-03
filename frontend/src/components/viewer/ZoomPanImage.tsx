import { useEffect, useRef, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';
import { Maximize2, Minus, Plus } from 'lucide-react';
import { cn } from '@/utils/cn';
import { MAX_ZOOM, type ZoomPan } from './useZoomPan';

interface ZoomPanSurfaceProps {
  zoom: ZoomPan;
  children: ReactNode;
  label: string;
  className?: string;
}

/** Wheel/drag/keyboard zoom & pan. Children are stacked layers (image + heatmap). */
export function ZoomPanSurface({ zoom, children, label, className }: ZoomPanSurfaceProps) {
  const drag = useRef<{ x: number; y: number } | null>(null);
  const surface = useRef<HTMLDivElement>(null);
  const { transform, zoomBy, panBy, reset } = zoom;

  // Native, non-passive listener so wheel-zoom doesn't also scroll the page.
  useEffect(() => {
    const el = surface.current;
    if (!el) return;
    const onWheel = (e: globalThis.WheelEvent) => {
      e.preventDefault();
      zoomBy(e.deltaY < 0 ? 1.15 : 1 / 1.15);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomBy]);
  const onPointerDown = (e: PointerEvent) => {
    if (transform.scale === 1) return;
    drag.current = { x: e.clientX, y: e.clientY };
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: PointerEvent) => {
    if (!drag.current) return;
    panBy(e.clientX - drag.current.x, e.clientY - drag.current.y);
    drag.current = { x: e.clientX, y: e.clientY };
  };
  const onPointerUp = () => {
    drag.current = null;
  };
  const onKeyDown = (e: KeyboardEvent) => {
    const step = 40;
    const map: Record<string, () => void> = {
      '+': () => zoomBy(1.25),
      '=': () => zoomBy(1.25),
      '-': () => zoomBy(0.8),
      '0': reset,
      ArrowLeft: () => panBy(step, 0),
      ArrowRight: () => panBy(-step, 0),
      ArrowUp: () => panBy(0, step),
      ArrowDown: () => panBy(0, -step),
    };
    const fn = map[e.key];
    if (fn) {
      e.preventDefault();
      fn();
    }
  };

  return (
    <div
      role="img"
      aria-label={`${label}. Use plus and minus to zoom, arrow keys to pan, 0 to reset.`}
      ref={surface}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={reset}
      onKeyDown={onKeyDown}
      className={cn(
        'relative h-full w-full touch-none overflow-hidden rounded-xl',
        transform.scale > 1 ? 'cursor-grab active:cursor-grabbing' : 'cursor-zoom-in',
        className,
      )}
    >
      <div
        className="relative flex h-full w-full items-center justify-center transition-transform duration-75 ease-out will-change-transform"
        style={{
          transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
        }}
      >
        {children}
      </div>
    </div>
  );
}

export function ZoomControls({ zoom, className }: { zoom: ZoomPan; className?: string }) {
  const btn =
    'grid h-8 w-8 place-items-center rounded-lg text-slate-300 hover:bg-viewer-line hover:text-white disabled:opacity-40';
  return (
    <div
      className={cn(
        'flex items-center gap-0.5 rounded-xl border border-viewer-line bg-viewer-panel/90 p-0.5 backdrop-blur',
        className,
      )}
    >
      <button
        type="button"
        className={btn}
        onClick={() => zoom.zoomBy(0.8)}
        aria-label="Zoom out"
        disabled={zoom.transform.scale <= 1}
      >
        <Minus className="h-4 w-4" />
      </button>
      <span className="num w-11 text-center text-xs text-slate-300" aria-live="polite">
        {Math.round(zoom.transform.scale * 100)}%
      </span>
      <button
        type="button"
        className={btn}
        onClick={() => zoom.zoomBy(1.25)}
        aria-label="Zoom in"
        disabled={zoom.transform.scale >= MAX_ZOOM}
      >
        <Plus className="h-4 w-4" />
      </button>
      <button type="button" className={btn} onClick={zoom.reset} aria-label="Reset zoom">
        <Maximize2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
