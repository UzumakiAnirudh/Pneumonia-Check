import { Clock, Cpu, Info, Microscope, ScanEye, Target } from 'lucide-react';
import type { ModelResult } from '@/api/types';
import { ConfidenceBar } from '@/components/ui/ConfidenceBar';
import { PredictionLabel } from '@/components/result/PredictionLabel';
import { ReliabilityBadge } from '@/components/result/ReliabilityBadge';
import { ProbabilityChart } from '@/components/result/ProbabilityChart';
import { LABELS } from '@/utils/labels';
import { getReliability } from '@/utils/reliability';
import { useSettings } from '@/store/settingsStore';
import { ms } from '@/utils/format';
import { cn } from '@/utils/cn';

export function SubtypeNote({ className }: { className?: string }) {
  return (
    <p
      className={cn(
        'flex items-start gap-2 rounded-lg bg-viral/5 px-3 py-2 text-xs text-ink-muted',
        className,
      )}
    >
      <Microscope className="mt-0.5 h-3.5 w-3.5 shrink-0 text-viral-ink" aria-hidden />
      Viral vs bacterial distinction from X-ray alone is less reliable; confirm with clinical and
      laboratory tests.
    </p>
  );
}

export function ResultsPanel({
  result,
  compact = false,
}: {
  result: ModelResult;
  compact?: boolean;
}) {
  const threshold = useSettings((s) => s.confidenceThreshold);
  const reliability = getReliability(result, threshold);
  const s1 = result.stage1;
  const s2 = result.stage2;
  const ex = result.explanation;

  return (
    <div className="space-y-5">
      <div className="space-y-4">
        <PredictionLabel
          label={s1.label}
          stage="Stage 1 · Detection"
          size={compact ? 'md' : 'lg'}
        />
        <ConfidenceBar
          value={s1.confidence}
          tone={LABELS[s1.label].tone}
          label={`Calibrated confidence${s1.temperature !== 1 ? ` (T = ${s1.temperature.toFixed(2)})` : ''}`}
          threshold={threshold}
        />
      </div>

      {s2 && (
        <div className="space-y-3 border-t border-border pt-5">
          <PredictionLabel label={s2.label} stage="Stage 2 · Pneumonia type" size="md" />
          <ConfidenceBar
            value={s2.confidence}
            tone={LABELS[s2.label].tone}
            label="Calibrated confidence"
            threshold={threshold}
            size="sm"
          />
          <SubtypeNote />
        </div>
      )}

      <ReliabilityBadge reliability={reliability} />

      <div className="border-t border-border pt-5">
        <h3 className="mb-3 text-sm font-semibold">Probability breakdown</h3>
        <ProbabilityChart
          probabilities={result.class_probabilities}
          highlight={result.stage2 ? result.final_label : result.stage1.label}
          compact={compact}
        />
      </div>

      {ex && (
        <div className="space-y-2.5 border-t border-border pt-5">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <ScanEye className="h-4 w-4 text-accent" aria-hidden /> What the model looked at
          </h3>
          <p className="text-[15px] text-ink">{ex.description}</p>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5 text-ink-muted">
              <Target className="h-3.5 w-3.5" aria-hidden />
              Attention inside lung region:{' '}
              <span className="num font-semibold text-ink">
                {ex.lung_attention_pct.toFixed(0)}%
              </span>
              {typeof ex.lung_area_pct === 'number' && (
                <span title="Share of the image covered by the lungs — the in-lung attention expected by chance">
                  (lungs cover <span className="num">{ex.lung_area_pct.toFixed(0)}%</span> of the
                  image)
                </span>
              )}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-2 px-2.5 py-1.5 text-ink-muted">
              <Info className="h-3.5 w-3.5" aria-hidden />
              {ex.method} · target{' '}
              {LABELS[ex.target_label as keyof typeof LABELS]?.text ?? ex.target_label}
            </span>
          </div>
          {ex.lung_attention_pct < (ex.lung_area_pct ?? 25) && (
            <p className="text-xs text-warning-ink">
              Attention is not concentrated on the lung fields (no more than chance) — the
              prediction may rely on non-anatomical cues.
            </p>
          )}
        </div>
      )}

      <dl className="grid grid-cols-2 gap-3 border-t border-border pt-5 text-sm">
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-ink-muted">
            <Cpu className="h-3.5 w-3.5" aria-hidden /> Model
          </dt>
          <dd className="font-medium">{result.model_name}</dd>
          <dd className="text-xs text-ink-muted">
            {result.mode === 'two_stage' ? 'Two-stage hierarchy' : 'Single 3-class model'}
          </dd>
        </div>
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-ink-muted">
            <Clock className="h-3.5 w-3.5" aria-hidden /> Inference time
          </dt>
          <dd className="num font-medium">{ms(result.inference_ms)}</dd>
        </div>
      </dl>
    </div>
  );
}
