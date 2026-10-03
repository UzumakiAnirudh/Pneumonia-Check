import { useState } from 'react';
import { motion } from 'framer-motion';
import { Columns2, Flame, ImageIcon, Layers } from 'lucide-react';
import type { Explanation } from '@/api/types';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Slider } from '@/components/ui/Slider';
import { HeatmapLegend } from '@/components/viewer/HeatmapLegend';
import { ZoomControls, ZoomPanSurface } from '@/components/viewer/ZoomPanImage';
import { useZoomPan } from '@/components/viewer/useZoomPan';
import { pct } from '@/utils/format';
import { cn } from '@/utils/cn';

export type ViewMode = 'original' | 'overlay' | 'heatmap' | 'split';

interface LayersProps {
  imageSrc: string;
  heatmapSrc?: string;
  opacity: number;
  showHeat: boolean;
  heatOnly?: boolean;
  alt: string;
}

/** Original + heatmap stacked; heatmap opacity == overlay blend weight. */
function ImageLayers({ imageSrc, heatmapSrc, opacity, showHeat, heatOnly, alt }: LayersProps) {
  return (
    <div className="relative max-h-full max-w-full">
      <img
        src={imageSrc}
        alt={alt}
        draggable={false}
        className={cn(
          'block max-h-[min(68vh,640px)] max-w-full select-none object-contain',
          heatOnly && 'invisible',
        )}
      />
      {heatmapSrc && showHeat && (
        <motion.img
          key={heatmapSrc}
          src={heatmapSrc}
          alt=""
          aria-hidden
          draggable={false}
          initial={{ opacity: 0 }}
          animate={{ opacity: heatOnly ? 1 : opacity }}
          transition={{ duration: 0.6 }}
          className="absolute inset-0 h-full w-full select-none object-contain"
        />
      )}
    </div>
  );
}

interface ExplanationViewerProps {
  imageSrc: string;
  explanation: Explanation | null;
  title?: string;
  compact?: boolean;
  defaultMode?: ViewMode;
}

export function ExplanationViewer({
  imageSrc,
  explanation,
  title,
  compact = false,
  defaultMode = 'overlay',
}: ExplanationViewerProps) {
  const [mode, setMode] = useState<ViewMode>(explanation ? defaultMode : 'original');
  const [opacity, setOpacity] = useState(0.45);
  const zoom = useZoomPan();
  const heat = explanation?.heatmap_png;

  const modes = [
    {
      value: 'original' as const,
      label: 'Original',
      icon: <ImageIcon className="h-3.5 w-3.5" aria-hidden />,
    },
    {
      value: 'overlay' as const,
      label: 'Overlay',
      icon: <Layers className="h-3.5 w-3.5" aria-hidden />,
      disabled: !heat,
    },
    {
      value: 'heatmap' as const,
      label: 'Heatmap',
      icon: <Flame className="h-3.5 w-3.5" aria-hidden />,
      disabled: !heat,
    },
    ...(compact
      ? []
      : [
          {
            value: 'split' as const,
            label: 'Side by side',
            icon: <Columns2 className="h-3.5 w-3.5" aria-hidden />,
            disabled: !heat,
          },
        ]),
  ];

  const modeLabel = {
    original: 'original X-ray',
    overlay: 'Grad-CAM overlay',
    heatmap: 'Grad-CAM heatmap',
    split: 'side-by-side view',
  }[mode];

  return (
    <section
      className={cn(
        'viewer-panel flex flex-col p-3',
        compact ? 'min-h-[360px]' : 'min-h-[460px] sm:min-h-[600px]',
      )}
      aria-label={title ?? 'X-ray viewer'}
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <SegmentedControl
          label="Viewer mode"
          options={modes}
          value={mode}
          onChange={setMode}
          variant="viewer"
          size="sm"
        />
        <ZoomControls zoom={zoom} />
      </div>

      <div
        className={cn(
          'relative flex-1 overflow-hidden rounded-xl bg-viewer-panel',
          mode === 'split' && 'grid grid-cols-2 gap-2 bg-transparent',
        )}
      >
        {mode === 'split' ? (
          (['original', 'overlay'] as const).map((pane) => (
            <div key={pane} className="relative overflow-hidden rounded-xl bg-viewer-panel">
              <span className="absolute left-2 top-2 z-10 rounded-md bg-viewer/80 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                {pane === 'original' ? 'Original' : 'Grad-CAM overlay'}
              </span>
              <ZoomPanSurface
                zoom={zoom}
                label={pane === 'original' ? 'Original X-ray' : 'Grad-CAM overlay'}
              >
                <ImageLayers
                  imageSrc={imageSrc}
                  heatmapSrc={heat}
                  opacity={opacity}
                  showHeat={pane === 'overlay'}
                  alt={`${pane} chest X-ray`}
                />
              </ZoomPanSurface>
            </div>
          ))
        ) : (
          <ZoomPanSurface zoom={zoom} label={`Chest X-ray, ${modeLabel}`}>
            <ImageLayers
              imageSrc={imageSrc}
              heatmapSrc={heat}
              opacity={opacity}
              showHeat={mode === 'overlay' || mode === 'heatmap'}
              heatOnly={mode === 'heatmap'}
              alt={`Chest X-ray, ${modeLabel}`}
            />
          </ZoomPanSurface>
        )}
        <span className="pointer-events-none absolute bottom-2 left-2 rounded bg-viewer/70 px-1.5 text-[10px] font-semibold tracking-wider text-slate-400">
          R
        </span>
        <span className="pointer-events-none absolute bottom-2 right-2 rounded bg-viewer/70 px-1.5 text-[10px] font-semibold tracking-wider text-slate-400">
          L
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-1">
        {heat ? (
          <>
            <Slider
              label="Overlay opacity"
              value={opacity}
              min={0}
              max={1}
              step={0.05}
              onChange={setOpacity}
              format={(v) => pct(v, 0)}
              variant="viewer"
              className="w-full max-w-xs"
            />
            <HeatmapLegend />
          </>
        ) : (
          <p className="text-xs text-slate-500">No explanation available for this result.</p>
        )}
      </div>
    </section>
  );
}
