import { useState } from 'react';
import { Images, Loader2 } from 'lucide-react';
import { useSamples } from '@/api/hooks';
import { api } from '@/api/client';
import type { SampleImage } from '@/api/types';
import { LABELS, TONE_HEX } from '@/utils/labels';

export function SampleSelector({
  onSelect,
  disabled,
}: {
  onSelect: (file: File, sample: SampleImage) => void;
  disabled?: boolean;
}) {
  const samples = useSamples();
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pick = async (sample: SampleImage) => {
    setLoadingId(sample.id);
    setError(null);
    try {
      onSelect(await api.sampleFile(sample), sample);
    } catch {
      setError('Could not load that sample image.');
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <Images className="h-4 w-4 text-ink-muted" aria-hidden />
        <h3 className="text-sm font-semibold">Use a sample X-ray</h3>
      </div>
      {samples.isLoading && <div className="h-20 animate-pulse rounded-xl bg-surface-2" />}
      {samples.isError && (
        <p className="text-sm text-ink-muted">Samples are unavailable while the API is offline.</p>
      )}
      {samples.data && (
        <ul className="grid grid-cols-3 gap-2.5" aria-label="Sample X-rays">
          {samples.data.slice(0, 6).map((s) => {
            const meta = LABELS[s.label];
            const Icon = meta.icon;
            return (
              <li key={s.id}>
                <button
                  type="button"
                  disabled={disabled || loadingId !== null}
                  onClick={() => pick(s)}
                  title={s.description}
                  className="group relative block w-full overflow-hidden rounded-xl border border-border bg-viewer text-left transition hover:border-accent focus-visible:border-accent disabled:opacity-60"
                >
                  <img
                    src={s.url}
                    alt={`${s.title} sample chest X-ray`}
                    className="aspect-square w-full object-cover opacity-85 transition group-hover:opacity-100"
                    loading="lazy"
                  />
                  <span
                    className="absolute inset-x-1.5 bottom-1.5 flex items-center justify-center gap-1 rounded-md bg-viewer/85 px-1.5 py-1 text-[11px] font-semibold backdrop-blur"
                    style={{ color: TONE_HEX[meta.tone] }}
                  >
                    {loadingId === s.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                    ) : (
                      <Icon className="h-3 w-3" aria-hidden />
                    )}
                    <span className="text-slate-100">{s.title}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {samples.data?.some((s) => s.synthetic) && (
        <p className="mt-2 text-xs text-ink-muted">
          Bundled samples are synthetic phantoms for demos — replace them with consented or
          public-dataset images.
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-sm text-pneumonia-ink">
          {error}
        </p>
      )}
    </div>
  );
}
