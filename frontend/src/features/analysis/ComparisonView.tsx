import type { PredictResponse } from '@/api/types';
import { MODEL_META } from '@/utils/labels';
import { useChartTheme } from '@/utils/theme';
import { AgreementBanner } from './AgreementBanner';
import { ExplanationViewer } from './ExplanationViewer';
import { ResultsPanel } from './ResultsPanel';

export function ComparisonView({ data }: { data: PredictResponse }) {
  const { series } = useChartTheme();
  return (
    <div className="space-y-6">
      {data.agreement && <AgreementBanner agreement={data.agreement} />}
      <div className="grid gap-6 xl:grid-cols-2">
        {data.results.map((r) => (
          <article
            key={r.model}
            className="card overflow-hidden"
            aria-label={`${MODEL_META[r.model].name} result`}
          >
            <header className="flex items-center gap-2.5 border-b border-border px-5 py-3.5">
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: series[r.model] }}
                aria-hidden
              />
              <h2 className="font-semibold">{MODEL_META[r.model].name}</h2>
              <span className="text-sm text-ink-muted">· {MODEL_META[r.model].family}</span>
            </header>
            <div className="space-y-5 p-4 sm:p-5">
              <ExplanationViewer
                imageSrc={data.image_png}
                explanation={r.explanation}
                title={`${MODEL_META[r.model].name} viewer`}
                compact
              />
              <ResultsPanel result={r} compact />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
