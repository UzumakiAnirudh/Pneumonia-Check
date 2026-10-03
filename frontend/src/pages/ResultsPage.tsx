import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Columns2,
  FileDown,
  FlaskConical,
  History,
  RotateCcw,
  ScanSearch,
  TriangleAlert,
} from 'lucide-react';
import { useHistoryItem } from '@/api/hooks';
import type { PredictResponse } from '@/api/types';
import { Button, ButtonLink } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Disclaimer } from '@/components/ui/Disclaimer';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { ExplanationViewer } from '@/features/analysis/ExplanationViewer';
import { ResultsPanel } from '@/features/analysis/ResultsPanel';
import { ComparisonView } from '@/features/analysis/ComparisonView';
import { ReportTemplate } from '@/features/report/ReportTemplate';
import { generateReportPdf } from '@/features/report/generateReport';
import { useAnalysis } from '@/store/analysisStore';
import { useSettings } from '@/store/settingsStore';
import { dateTime, ms } from '@/utils/format';

function ResultsContent({ data, fromHistory }: { data: PredictResponse; fromHistory: boolean }) {
  const navigate = useNavigate();
  const threshold = useSettings((s) => s.confidenceThreshold);
  const hasImage = useAnalysis((s) => Boolean(s.image));
  const reset = useAnalysis((s) => s.reset);
  const reportRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const comparing = data.results.length > 1;
  const single = data.results[0];

  const download = async () => {
    if (!reportRef.current) return;
    setExporting(true);
    setExportError(null);
    try {
      await generateReportPdf(reportRef.current, `pneumoscan-report-${data.id.slice(0, 8)}.pdf`);
    } catch {
      setExportError('Could not generate the PDF. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const canCompare = !comparing && hasImage && !fromHistory;

  return (
    <div>
      <PageHeader
        eyebrow={fromHistory ? 'History' : 'Analysis results'}
        title={comparing ? 'Model comparison' : 'Analysis results'}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>{dateTime(data.created_at)}</span>
            {data.source_name && <span className="truncate">· {data.source_name}</span>}
            <span className="num">· total {ms(data.total_ms)}</span>
          </span>
        }
        actions={
          <>
            <Button
              variant="outline"
              onClick={download}
              loading={exporting}
              icon={<FileDown className="h-4 w-4" />}
            >
              Download Report (PDF)
            </Button>
            {!comparing && (
              <Button
                variant="outline"
                disabled={!canCompare}
                title={
                  canCompare
                    ? 'Run both models on this image'
                    : 'Re-upload the original image to compare models'
                }
                onClick={() => navigate('/analyze', { state: { autorun: 'both' } })}
                icon={<Columns2 className="h-4 w-4" />}
              >
                Compare Models
              </Button>
            )}
            <Button
              onClick={() => {
                reset();
                navigate('/analyze');
              }}
              icon={<RotateCcw className="h-4 w-4" />}
            >
              Analyze Another
            </Button>
          </>
        }
      />

      <div className="mb-5 flex flex-wrap gap-2">
        {data.is_mock && (
          <Badge tone="warning" icon={<FlaskConical className="h-3.5 w-3.5" aria-hidden />}>
            Demo mode — simulated model outputs
          </Badge>
        )}
        {fromHistory && (
          <Badge tone="neutral" icon={<History className="h-3.5 w-3.5" aria-hidden />}>
            Reopened from history (thumbnail resolution)
          </Badge>
        )}
        {data.validation.warnings.map((w) => (
          <Badge
            key={w}
            tone="warning"
            icon={<TriangleAlert className="h-3.5 w-3.5" aria-hidden />}
          >
            {w}
          </Badge>
        ))}
      </div>
      {exportError && (
        <p role="alert" className="mb-4 text-sm text-pneumonia-ink">
          {exportError}
        </p>
      )}

      {comparing ? (
        <ComparisonView data={data} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(340px,1fr)]">
          <ExplanationViewer imageSrc={data.image_png} explanation={single.explanation} />
          <Card className="p-5 sm:p-6">
            <ResultsPanel result={single} />
          </Card>
        </div>
      )}

      <Disclaimer className="mt-6" />

      {/* Off-screen report source for html2canvas */}
      <div aria-hidden className="pointer-events-none fixed -left-[10000px] top-0">
        <ReportTemplate ref={reportRef} data={data} threshold={threshold} />
      </div>
    </div>
  );
}

export function ResultsPage() {
  const { id } = useParams();
  const current = useAnalysis((s) => s.result);
  const historyItem = useHistoryItem(id && id !== current?.id ? id : undefined);

  if (id && id !== current?.id) {
    if (historyItem.isLoading)
      return (
        <div className="h-96 animate-pulse rounded-card bg-surface-2" aria-label="Loading result" />
      );
    if (historyItem.data) return <ResultsContent data={historyItem.data} fromHistory />;
    return (
      <Card>
        <EmptyState
          icon={<History className="h-6 w-6" />}
          title="Result not found"
          description="This analysis is no longer in history. It may have been deleted."
          action={
            <ButtonLink to="/history" variant="outline">
              Back to history
            </ButtonLink>
          }
        />
      </Card>
    );
  }

  if (!current) {
    return (
      <Card>
        <EmptyState
          icon={<ScanSearch className="h-6 w-6" />}
          title="No analysis yet"
          description="Upload a chest X-ray on the Analyze page to see predictions and Grad-CAM explanations here."
          action={<ButtonLink to="/analyze">Start Analysis</ButtonLink>}
        />
      </Card>
    );
  }

  return <ResultsContent data={current} fromHistory={false} />;
}
