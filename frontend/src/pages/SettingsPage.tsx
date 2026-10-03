import { Laptop, Moon, RefreshCw, Sun } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Slider } from '@/components/ui/Slider';
import { Switch } from '@/components/ui/Switch';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { StatusDot } from '@/components/ui/StatusDot';
import { useApiStatus } from '@/components/layout/useApiStatus';
import { TrainingPanel } from '@/components/layout/TrainingStatus';
import { DEFAULT_THRESHOLD, useSettings, type ThemePreference } from '@/store/settingsStore';
import type { ModelChoice } from '@/api/types';
import { pct } from '@/utils/format';

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-t border-border py-5 first:border-t-0 first:pt-0 last:pb-0">
      {children}
    </div>
  );
}

export function SettingsPage() {
  const s = useSettings();
  const { status, label, health } = useApiStatus();
  const h = health.data;

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Preferences"
        title="Settings"
        description="Saved in this browser only."
      />

      <div className="space-y-6">
        <Card className="p-5 sm:p-6">
          <CardHeader title="Display & analysis" className="mb-5" />
          <Row>
            <p className="mb-2 font-medium">Theme</p>
            <SegmentedControl<ThemePreference>
              label="Theme"
              value={s.theme}
              onChange={s.setTheme}
              options={[
                { value: 'light', label: 'Light', icon: <Sun className="h-4 w-4" aria-hidden /> },
                { value: 'dark', label: 'Dark', icon: <Moon className="h-4 w-4" aria-hidden /> },
                {
                  value: 'system',
                  label: 'System',
                  icon: <Laptop className="h-4 w-4" aria-hidden />,
                },
              ]}
            />
          </Row>
          <Row>
            <p className="mb-2 font-medium">Default model</p>
            <SegmentedControl<ModelChoice>
              label="Default model"
              value={s.defaultModel}
              onChange={s.setDefaultModel}
              options={[
                { value: 'densenet', label: 'DenseNet121' },
                { value: 'swin', label: 'Swin Transformer' },
                { value: 'both', label: 'Compare Both' },
              ]}
            />
          </Row>
          <Row>
            <div className="mb-2 flex items-baseline justify-between gap-4">
              <p className="font-medium">Confidence threshold</p>
              {s.confidenceThreshold !== DEFAULT_THRESHOLD && (
                <button
                  type="button"
                  className="link text-sm"
                  onClick={() => s.setConfidenceThreshold(DEFAULT_THRESHOLD)}
                >
                  Reset to {pct(DEFAULT_THRESHOLD, 0)}
                </button>
              )}
            </div>
            <p className="mb-3 text-sm text-ink-muted">
              Results whose calibrated confidence is below this value (at any stage) are flagged
              “Low confidence — recommend expert review”.
            </p>
            <Slider
              label="Threshold"
              hideLabel
              value={s.confidenceThreshold}
              min={0.5}
              max={0.99}
              step={0.01}
              onChange={s.setConfidenceThreshold}
              format={(v) => pct(v, 0)}
            />
          </Row>
          <Row>
            <Switch
              id="history-toggle"
              label="Save analysis history"
              description="Stores a small thumbnail, results and timestamp. When off, images are processed in memory only and nothing is kept."
              checked={s.historyEnabled}
              onChange={s.setHistoryEnabled}
            />
            {h && !h.history_enabled && s.historyEnabled && (
              <p className="mt-2 text-sm text-warning-ink">
                History is disabled on the server (HISTORY_ENABLED=false).
              </p>
            )}
          </Row>
        </Card>

        <Card className="p-5 sm:p-6">
          <CardHeader title="Model version & training" className="mb-4" />
          <TrainingPanel />
        </Card>

        <Card className="p-5 sm:p-6">
          <CardHeader
            title="API status"
            actions={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => health.refetch()}
                loading={health.isFetching}
                icon={<RefreshCw className="h-4 w-4" />}
              >
                Refresh
              </Button>
            }
            className="mb-4"
          />
          <div className="flex items-center gap-2.5" role="status">
            <StatusDot status={status} pulse={status === 'online'} />
            <span className="font-medium">{label}</span>
          </div>
          {health.isError && (
            <p className="mt-3 text-sm text-ink-muted">
              Start the backend with{' '}
              <code className="num rounded bg-surface-2 px-1.5 py-0.5">
                uvicorn app.main:app --port 8000
              </code>
              .
            </p>
          )}
          {h && (
            <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-ink-muted">Models</dt>
                <dd>
                  {h.use_mock_models ? 'Mock models (simulated outputs)' : 'Trained weights'} ·{' '}
                  {h.classification_mode === 'two_stage' ? 'two-stage' : '3-class'}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Device · version</dt>
                <dd className="num">
                  {h.device} · v{h.version}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Input validator</dt>
                <dd>
                  {h.validator.method === 'model'
                    ? 'Learned classifier (MobileNetV3)'
                    : 'Heuristic fallback'}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Calibration</dt>
                <dd>
                  {h.calibration.loaded ? 'Temperature scaling loaded' : 'Not calibrated (T = 1)'}
                </dd>
              </div>
              {h.models.map((m) => (
                <div key={m.key}>
                  <dt className="text-xs text-ink-muted">{m.name}</dt>
                  <dd className="flex flex-wrap gap-1.5">
                    {Object.keys(m.weights).length === 0 && (
                      <span>{m.ready ? 'Ready' : 'Not ready'}</span>
                    )}
                    {Object.entries(m.weights).map(([k, ok]) => (
                      <Badge key={k} tone={ok ? 'normal' : 'neutral'}>
                        {k} {ok ? '✓' : '—'}
                      </Badge>
                    ))}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </Card>
      </div>
    </div>
  );
}
