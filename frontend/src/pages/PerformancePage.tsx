import { useState } from 'react';
import {
  BarChart3,
  FlaskConical,
  Globe2,
  Grid3x3,
  Images,
  LineChart as LineIcon,
  Table2,
  Target,
  Users,
} from 'lucide-react';
import { useMetrics } from '@/api/hooks';
import type {
  MetricSummary,
  MetricsResponse,
  ModelKey,
  ModelTaskMetrics,
  TaskMetrics,
} from '@/api/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TabPanel, Tabs } from '@/components/ui/Tabs';
import { MetricCards } from '@/features/performance/MetricCards';
import { ConfusionMatrix } from '@/features/performance/ConfusionMatrix';
import { RocChart } from '@/features/performance/RocChart';
import { CalibrationChart } from '@/features/performance/CalibrationChart';
import { ComparisonTable } from '@/features/performance/ComparisonTable';
import { TASK_LABELS } from '@/features/performance/labels';
import { TrainingCurves } from '@/features/performance/TrainingCurves';
import { PopulationTable } from '@/features/performance/PopulationTable';
import { GradcamGallery } from '@/features/performance/GradcamGallery';
import { MODEL_META } from '@/utils/labels';
import { dateTime } from '@/utils/format';

type Tab = 'internal' | 'external';
type TaskKey = keyof ModelTaskMetrics;

function pick<T>(
  internal: Partial<Record<ModelKey, ModelTaskMetrics>>,
  task: TaskKey,
  fn: (t: TaskMetrics) => T | null | undefined,
): Partial<Record<ModelKey, T>> {
  const out: Partial<Record<ModelKey, T>> = {};
  for (const m of Object.keys(internal) as ModelKey[]) {
    const t = internal[m]?.[task];
    const v = t ? fn(t) : null;
    if (v) out[m] = v;
  }
  return out;
}

function TaskSection({
  internal,
  task,
}: {
  internal: Partial<Record<ModelKey, ModelTaskMetrics>>;
  task: TaskKey;
}) {
  const metrics = pick(internal, task, (t) => t.metrics);
  const rocs = pick(internal, task, (t) => t.roc);
  const calib = pick(internal, task, (t) => t.calibration);
  const models = Object.keys(metrics) as ModelKey[];
  const sample = internal[models[0]]?.[task];
  return (
    <div className="space-y-6">
      <MetricCards metrics={metrics} />
      {sample && (
        <p className="-mt-3 text-xs text-ink-muted">
          Positive class: <span className="font-medium text-ink">{sample.positive_label}</span> · n
          = <span className="num">{sample.n}</span> test images
        </p>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        {Object.keys(rocs).length > 0 ? (
          <Card className="p-5">
            <CardHeader
              as="h3"
              icon={<LineIcon className="h-5 w-5" />}
              title="ROC curves"
              description="Both models on one chart."
              className="mb-3"
            />
            <RocChart curves={rocs} />
          </Card>
        ) : (
          <Card className="p-5">
            <CardHeader
              as="h3"
              icon={<LineIcon className="h-5 w-5" />}
              title="ROC curves"
              className="mb-3"
            />
            <p className="text-sm text-ink-muted">
              ROC curves are reported for the binary stages; see the macro ROC-AUC above.
            </p>
          </Card>
        )}
        {Object.keys(calib).length > 0 && (
          <Card className="p-5">
            <CardHeader
              as="h3"
              icon={<Target className="h-5 w-5" />}
              title="Calibration"
              description="Reliability diagram after temperature scaling."
              className="mb-3"
            />
            <CalibrationChart curves={calib} />
          </Card>
        )}
      </div>

      <Card className="p-5">
        <CardHeader
          as="h3"
          icon={<Grid3x3 className="h-5 w-5" />}
          title="Confusion matrices"
          description="Hover or focus a cell for details."
          className="mb-4"
        />
        <div className="grid gap-8 lg:grid-cols-2">
          {models.map((m) => {
            const t = internal[m]![task]!;
            return (
              <ConfusionMatrix
                key={m}
                matrix={t.confusion_matrix}
                labels={t.labels}
                title={MODEL_META[m].name}
              />
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function InternalTab({ data }: { data: MetricsResponse }) {
  const tasks = (['stage1', 'stage2', 'pipeline', 'three_class'] as TaskKey[]).filter((t) =>
    Object.values(data.internal).some((m) => m?.[t]),
  );
  const [task, setTask] = useState<TaskKey>(tasks[0] ?? 'stage1');
  const curveTasks = Array.from(
    new Set(Object.values(data.training_curves).flatMap((c) => Object.keys(c ?? {}))),
  );
  const [curveTask, setCurveTask] = useState(curveTasks[0] ?? 'stage1');
  const curveLogs: Partial<
    Record<ModelKey, NonNullable<MetricsResponse['training_curves'][ModelKey]>[string]>
  > = {};
  for (const m of Object.keys(data.training_curves) as ModelKey[]) {
    const logs = data.training_curves[m]?.[curveTask];
    if (logs?.length) curveLogs[m] = logs;
  }

  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={<BarChart3 className="h-6 w-6" />}
        title="No internal results yet"
        description="Run training/evaluate.py to populate this view."
      />
    );
  }

  return (
    <div className="space-y-8">
      <SegmentedControl<TaskKey>
        label="Task"
        value={task}
        onChange={setTask}
        options={tasks.map((t) => ({
          value: t,
          label: TASK_LABELS[t].split(' · ')[0] + (t === 'pipeline' ? ' (3-class)' : ''),
          description: TASK_LABELS[t],
        }))}
      />
      <p className="-mt-5 text-sm text-ink-muted">{TASK_LABELS[task]}</p>
      <TaskSection internal={data.internal} task={task} />

      <Card className="p-5">
        <CardHeader
          as="h3"
          icon={<Table2 className="h-5 w-5" />}
          title="DenseNet121 vs Swin Transformer"
          description="All metrics, internal test set. Best value per row in bold."
          className="mb-4"
        />
        <ComparisonTable internal={data.internal} />
      </Card>

      {data.by_domain && Object.keys(data.by_domain).length > 0 && (
        <Card className="p-5">
          <CardHeader
            as="h3"
            icon={<Users className="h-5 w-5" />}
            title="Performance by population"
            description="The same test set split into children and adults."
            className="mb-4"
          />
          <PopulationTable data={data.by_domain} />
        </Card>
      )}

      {curveTasks.length > 0 && (
        <Card className="p-5">
          <CardHeader
            as="h3"
            icon={<LineIcon className="h-5 w-5" />}
            title="Training curves"
            description="Solid lines: training. Dashed lines: validation."
            actions={
              curveTasks.length > 1 && (
                <SegmentedControl
                  label="Training curves task"
                  size="sm"
                  value={curveTask}
                  onChange={setCurveTask}
                  options={curveTasks.map((t) => ({
                    value: t,
                    label: TASK_LABELS[t]?.split(' · ')[0] ?? t,
                  }))}
                />
              )
            }
            className="mb-4"
          />
          <TrainingCurves logs={curveLogs} />
        </Card>
      )}

      <Card className="p-5">
        <CardHeader
          as="h3"
          icon={<Images className="h-5 w-5" />}
          title="Grad-CAM gallery"
          description="Correct predictions, misclassifications and failure cases (low confidence or attention outside the lungs)."
          className="mb-4"
        />
        <GradcamGallery items={data.gallery} />
      </Card>
    </div>
  );
}

function ExternalTab({ data }: { data: MetricsResponse }) {
  if (data.external.length === 0) {
    return (
      <EmptyState
        icon={<Globe2 className="h-6 w-6" />}
        title="No external validation yet"
        description="Run training/external_validate.py on RSNA or another public dataset to measure generalisation."
      />
    );
  }
  return (
    <div className="space-y-8">
      {data.external.map((ds) => {
        const models = Object.keys(ds.models) as ModelKey[];
        const metrics: Partial<Record<ModelKey, MetricSummary>> = {};
        const deltas: Partial<Record<ModelKey, Partial<MetricSummary>>> = {};
        const rocs: Partial<Record<ModelKey, NonNullable<TaskMetrics['roc']>>> = {};
        for (const m of models) {
          metrics[m] = ds.models[m]!.stage1.metrics;
          deltas[m] = ds.models[m]!.drop;
          const roc = ds.models[m]!.stage1.roc;
          if (roc) rocs[m] = roc;
        }
        return (
          <section key={ds.name} className="space-y-6" aria-labelledby={`ext-${ds.name}`}>
            <div>
              <h2 id={`ext-${ds.name}`} className="text-xl font-semibold">
                {ds.name}
              </h2>
              <p className="text-sm text-ink-muted">
                {ds.description} · n = <span className="num">{ds.n}</span>. Small numbers show the
                change versus the internal test set.
              </p>
            </div>
            <MetricCards metrics={metrics} deltas={deltas} />
            <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
              <Card className="p-5">
                <CardHeader
                  as="h3"
                  icon={<LineIcon className="h-5 w-5" />}
                  title="ROC curves · Stage 1"
                  className="mb-3"
                />
                {Object.keys(rocs).length > 0 ? (
                  <RocChart curves={rocs} />
                ) : (
                  <p className="text-sm text-ink-muted">
                    This set contains a single class, so ROC-AUC, sensitivity and precision are
                    undefined (shown as n/a). Specificity and accuracy measure how often normal
                    images are correctly left unflagged.
                  </p>
                )}
              </Card>
              <Card className="p-5">
                <CardHeader
                  as="h3"
                  icon={<Grid3x3 className="h-5 w-5" />}
                  title="Confusion matrices"
                  className="mb-4"
                />
                <div className="space-y-6">
                  {models.map((m) => (
                    <ConfusionMatrix
                      key={m}
                      matrix={ds.models[m]!.stage1.confusion_matrix}
                      labels={ds.models[m]!.stage1.labels}
                      title={MODEL_META[m].name}
                    />
                  ))}
                </div>
              </Card>
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default function PerformancePage() {
  const metrics = useMetrics();
  const [tab, setTab] = useState<Tab>('internal');

  return (
    <div>
      <PageHeader
        eyebrow="Evaluation"
        title="Model performance"
        description="Metrics exported by the training pipeline for DenseNet121 and Swin Transformer."
      />

      {metrics.isLoading && (
        <div
          className="h-96 animate-pulse rounded-card bg-surface-2"
          aria-label="Loading metrics"
        />
      )}
      {metrics.isError && (
        <Card>
          <EmptyState
            icon={<BarChart3 className="h-6 w-6" />}
            title="Metrics unavailable"
            description={metrics.error.message}
          />
        </Card>
      )}

      {metrics.data && (
        <>
          {metrics.data.is_demo && (
            <div
              role="note"
              className="mb-6 flex items-start gap-3 rounded-card border border-warning/50 bg-warning/10 px-5 py-4 text-warning-ink"
            >
              <FlaskConical className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
              <div className="text-sm">
                <p className="font-semibold">Illustrative placeholder metrics</p>
                <p>
                  These numbers are simulated so the dashboard can be demonstrated before training.
                  They are not results of a trained model. Run{' '}
                  <code className="num">training/evaluate.py</code> to replace them with real
                  results.
                </p>
              </div>
            </div>
          )}

          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <Tabs<Tab>
              label="Evaluation set"
              idPrefix="perf"
              value={tab}
              onChange={setTab}
              tabs={[
                { value: 'internal', label: 'Internal Test Set' },
                { value: 'external', label: 'External Validation' },
              ]}
            />
            <p className="text-xs text-ink-muted">
              {metrics.data.dataset.name} · updated {dateTime(metrics.data.generated_at)}
            </p>
          </div>

          <TabPanel idPrefix="perf" value={tab}>
            {tab === 'internal' ? (
              <InternalTab data={metrics.data} />
            ) : (
              <ExternalTab data={metrics.data} />
            )}
          </TabPanel>
        </>
      )}
    </div>
  );
}
