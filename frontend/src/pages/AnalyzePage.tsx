import { useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertOctagon,
  FileScan,
  Lock,
  RotateCcw,
  ScanSearch,
  TriangleAlert,
  X,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Disclaimer } from '@/components/ui/Disclaimer';
import { UploadZone } from '@/features/upload/UploadZone';
import { SampleSelector } from '@/features/upload/SampleSelector';
import { ModelSelector } from '@/features/upload/ModelSelector';
import { ProcessingImage, ProcessingSteps } from '@/features/analysis/ProcessingView';
import { useRunAnalysis } from '@/features/analysis/useRunAnalysis';
import { useAnalysis } from '@/store/analysisStore';
import { useSettings } from '@/store/settingsStore';
import type { ModelChoice } from '@/api/types';
import { getImageDimensions, isDicomFile } from '@/utils/image';
import { bytes } from '@/utils/format';

function ImageMeta() {
  const image = useAnalysis((s) => s.image);
  if (!image) return null;
  const { file, width, height } = image;
  const rows: [string, string][] = [
    ['File', image.sourceName ?? file.name],
    [
      'Resolution',
      width && height
        ? `${width} × ${height} px`
        : isDicomFile(file)
          ? 'Read on server (DICOM)'
          : '—',
    ],
    ['Size', bytes(file.size)],
    ['Format', isDicomFile(file) ? 'DICOM' : (file.type.split('/')[1] ?? 'unknown').toUpperCase()],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-xl bg-surface-2 p-3.5 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="text-xs text-ink-muted">{k}</dt>
          <dd className="num truncate text-[13px] text-ink" title={v}>
            {v}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function AnalyzePage() {
  const { image, status, validation, error, setImage, reset } = useAnalysis();
  const storeModel = useAnalysis((s) => s.model);
  const setModel = useAnalysis((s) => s.setModel);
  const defaultModel = useSettings((s) => s.defaultModel);
  const model: ModelChoice = storeModel ?? defaultModel;
  const { run, step } = useRunAnalysis();
  const location = useLocation();
  const navigate = useNavigate();
  const autoRan = useRef(false);

  const busy = status === 'validating' || status === 'analyzing';

  // "Compare Models" from the results page lands here with { autorun: 'both' }.
  useEffect(() => {
    const autorun = (location.state as { autorun?: ModelChoice } | null)?.autorun;
    if (autorun && image && !autoRan.current) {
      autoRan.current = true;
      navigate('.', { replace: true, state: null });
      void run(autorun);
    }
  }, [image, location.state, navigate, run]);

  const selectFile = async (file: File, sourceName: string | null = null) => {
    const dims = await getImageDimensions(file);
    setImage({
      file,
      previewUrl: isDicomFile(file) ? null : URL.createObjectURL(file),
      sourceName,
      width: dims?.width ?? null,
      height: dims?.height ?? null,
    });
  };

  return (
    <div>
      <PageHeader
        eyebrow="Workspace"
        title="Analyze a chest X-ray"
        description="Upload a frontal chest X-ray or pick a sample, choose a model, and run the analysis."
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.45fr)_minmax(340px,1fr)]">
        {/* Viewer */}
        <section
          aria-label="Image viewer"
          className="viewer-panel flex min-h-[420px] flex-col p-3 sm:min-h-[560px]"
        >
          <div className="mb-3 flex items-center justify-between gap-3 px-1">
            <div className="flex min-w-0 items-center gap-2 text-sm text-slate-300">
              <FileScan className="h-4 w-4 shrink-0 text-accent" aria-hidden />
              <span className="truncate">
                {image ? (image.sourceName ?? image.file.name) : 'No image loaded'}
              </span>
            </div>
            {image && !busy && (
              <div className="flex items-center gap-1">
                <UploadZone onFile={(f) => selectFile(f)} compact />
                <button
                  type="button"
                  onClick={reset}
                  className="grid h-7 w-7 place-items-center rounded-lg text-slate-400 hover:bg-viewer-line hover:text-white"
                  aria-label="Remove image"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
          <div className="relative flex-1">
            <AnimatePresence mode="wait">
              {!image ? (
                <motion.div
                  key="upload"
                  className="absolute inset-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <UploadZone onFile={(f) => selectFile(f)} />
                </motion.div>
              ) : busy ? (
                <motion.div
                  key="processing"
                  className="absolute inset-0"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <ProcessingImage src={image.previewUrl} alt="Chest X-ray being analysed" />
                </motion.div>
              ) : (
                <motion.div
                  key="preview"
                  className="absolute inset-0 flex items-center justify-center overflow-hidden rounded-xl bg-viewer-panel"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  {image.previewUrl ? (
                    <img
                      src={image.previewUrl}
                      alt="Uploaded chest X-ray preview"
                      className="max-h-full max-w-full object-contain"
                    />
                  ) : (
                    <div className="text-center text-slate-400">
                      <FileScan className="mx-auto mb-3 h-10 w-10 text-accent" aria-hidden />
                      <p className="font-medium text-slate-200">DICOM file loaded</p>
                      <p className="text-sm">
                        Preview appears after analysis; identifiers are stripped on the server.
                      </p>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </section>

        {/* Controls */}
        <div className="space-y-5">
          <Card className="space-y-5 p-5">
            <ModelSelector value={model} onChange={setModel} disabled={busy} />
            {image && <ImageMeta />}

            {status === 'rejected' && validation && (
              <div
                role="alert"
                className="rounded-xl border border-pneumonia/40 bg-pneumonia/10 p-4 text-sm"
              >
                <p className="flex items-center gap-2 font-semibold text-pneumonia-ink">
                  <AlertOctagon className="h-4 w-4" aria-hidden />
                  {validation.is_chest_xray
                    ? 'Image cannot be analysed'
                    : "This doesn't look like a chest X-ray."}
                </p>
                <p className="mt-1 text-ink">
                  {validation.is_chest_xray
                    ? validation.message
                    : 'Please upload a frontal chest X-ray image.'}
                </p>
                {validation.reasons.length > 0 && (
                  <ul className="mt-2 list-disc space-y-0.5 pl-5 text-ink-muted">
                    {validation.reasons.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {validation && validation.warnings.length > 0 && status !== 'rejected' && (
              <div className="rounded-xl border border-warning/50 bg-warning/10 p-3 text-sm text-warning-ink">
                <p className="flex items-center gap-2 font-semibold">
                  <TriangleAlert className="h-4 w-4" aria-hidden /> Image quality
                </p>
                <ul className="mt-1 list-disc pl-5">
                  {validation.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
            {status === 'error' && error && (
              <div
                role="alert"
                className="rounded-xl border border-pneumonia/40 bg-pneumonia/10 p-3 text-sm text-pneumonia-ink"
              >
                {error}
              </div>
            )}

            {busy ? (
              <div className="viewer-panel p-3" aria-live="polite">
                <ProcessingSteps current={step} />
              </div>
            ) : (
              <Button
                size="lg"
                className="w-full"
                disabled={!image}
                onClick={() => run(model)}
                icon={
                  status === 'rejected' || status === 'error' ? (
                    <RotateCcw className="h-5 w-5" />
                  ) : (
                    <ScanSearch className="h-5 w-5" />
                  )
                }
              >
                {status === 'rejected' || status === 'error' ? 'Try again' : 'Analyze'}
              </Button>
            )}
          </Card>

          <Card className="p-5">
            <SampleSelector
              onSelect={(file, sample) => selectFile(file, sample.title)}
              disabled={busy}
            />
          </Card>

          <div className="flex items-start gap-2.5 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink-muted">
            <Lock className="mt-0.5 h-4 w-4 shrink-0 text-primary-text" aria-hidden />
            <p>
              <strong className="font-semibold text-ink">Privacy:</strong> images are processed in
              memory and metadata is stripped. Nothing is stored unless history is enabled, in which
              case only a small thumbnail and the results are kept. Use patient images only with
              consent and appropriate approval.
            </p>
          </div>
          <Disclaimer compact />
        </div>
      </div>
    </div>
  );
}
