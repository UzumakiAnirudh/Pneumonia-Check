import { useCallback, useState } from 'react';

export interface ViewTransform {
  scale: number;
  x: number;
  y: number;
}

export const IDENTITY: ViewTransform = { scale: 1, x: 0, y: 0 };
const MIN = 1;
export const MAX_ZOOM = 6;

export function useZoomPan() {
  const [t, setT] = useState<ViewTransform>(IDENTITY);
  const zoomBy = useCallback((factor: number) => {
    setT((p) => {
      const scale = Math.min(MAX_ZOOM, Math.max(MIN, p.scale * factor));
      return scale === 1
        ? IDENTITY
        : { scale, x: (p.x * scale) / p.scale, y: (p.y * scale) / p.scale };
    });
  }, []);
  const panBy = useCallback((dx: number, dy: number) => {
    setT((p) => (p.scale === 1 ? p : { ...p, x: p.x + dx, y: p.y + dy }));
  }, []);
  const reset = useCallback(() => setT(IDENTITY), []);
  return { transform: t, setTransform: setT, zoomBy, panBy, reset };
}

export type ZoomPan = ReturnType<typeof useZoomPan>;
