import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FlaskConical, History, Search, Settings2, Trash2 } from 'lucide-react';
import { useClearHistory, useDeleteHistoryItem, useHistory } from '@/api/hooks';
import type { FinalLabel, HistoryItem, ModelKey } from '@/api/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Card } from '@/components/ui/Card';
import { Button, ButtonLink } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { LABELS, MODEL_META, TONE_CLASSES } from '@/utils/labels';
import { useSettings } from '@/store/settingsStore';
import { dateTime, pct } from '@/utils/format';
import { cn } from '@/utils/cn';

type LabelFilter = 'all' | FinalLabel;
type ModelFilter = 'all' | ModelKey | 'both';

function LabelPill({ label }: { label: FinalLabel | 'PNEUMONIA' }) {
  const meta = LABELS[label];
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-sm font-semibold',
        TONE_CLASSES[meta.tone].text,
      )}
    >
      <Icon className="h-4 w-4" aria-hidden />
      {meta.text}
    </span>
  );
}

function modelText(item: HistoryItem) {
  return item.models.length > 1 ? 'Both (compare)' : MODEL_META[item.models[0]].name;
}

export function HistoryPage() {
  const historyEnabled = useSettings((s) => s.historyEnabled);
  const history = useHistory();
  const del = useDeleteHistoryItem();
  const clear = useClearHistory();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [label, setLabel] = useState<LabelFilter>('all');
  const [model, setModel] = useState<ModelFilter>('all');
  const [confirmClear, setConfirmClear] = useState(false);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (history.data ?? []).filter((h) => {
      if (label !== 'all' && h.final_label !== label) return false;
      if (model === 'both' && h.models.length < 2) return false;
      if (
        (model === 'densenet' || model === 'swin') &&
        (h.models.length > 1 || h.models[0] !== model)
      )
        return false;
      if (!q) return true;
      return [h.source_name ?? '', LABELS[h.final_label].text, modelText(h), dateTime(h.created_at)]
        .join(' ')
        .toLowerCase()
        .includes(q);
    });
  }, [history.data, label, model, query]);

  const total = history.data?.length ?? 0;

  return (
    <div>
      <PageHeader
        eyebrow="Records"
        title="Analysis history"
        description="Your past analyses — private to your account. Stored as a small thumbnail plus results; click a row to reopen it."
        actions={
          total > 0 &&
          (confirmClear ? (
            <div className="flex items-center gap-2" role="group" aria-label="Confirm delete all">
              <span className="text-sm text-ink-muted">Delete all {total}?</span>
              <Button
                variant="danger"
                size="sm"
                loading={clear.isPending}
                onClick={() => clear.mutate(undefined, { onSuccess: () => setConfirmClear(false) })}
              >
                Delete all
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirmClear(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              onClick={() => setConfirmClear(true)}
              icon={<Trash2 className="h-4 w-4" />}
            >
              Delete all
            </Button>
          ))
        }
      />

      {!historyEnabled && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm">
          <span className="text-ink-muted">
            History saving is turned off — new analyses are not stored.
          </span>
          <ButtonLink
            to="/settings"
            variant="ghost"
            size="sm"
            icon={<Settings2 className="h-4 w-4" />}
          >
            Settings
          </ButtonLink>
        </div>
      )}

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-border p-4 lg:flex-row lg:items-center lg:justify-between">
          <label className="relative block w-full lg:max-w-xs">
            <span className="sr-only">Search history</span>
            <Search
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted"
              aria-hidden
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, label, model…"
              className="h-10 w-full rounded-xl border border-border bg-surface pl-9 pr-3 text-sm placeholder:text-ink-muted focus:border-accent"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <SegmentedControl<LabelFilter>
              label="Filter by result"
              size="sm"
              value={label}
              onChange={setLabel}
              options={[
                { value: 'all', label: 'All' },
                { value: 'NORMAL', label: 'Normal' },
                { value: 'BACTERIAL', label: 'Bacterial' },
                { value: 'VIRAL', label: 'Viral' },
              ]}
            />
            <SegmentedControl<ModelFilter>
              label="Filter by model"
              size="sm"
              value={model}
              onChange={setModel}
              options={[
                { value: 'all', label: 'Any model' },
                { value: 'densenet', label: 'DenseNet' },
                { value: 'swin', label: 'Swin' },
                { value: 'both', label: 'Both' },
              ]}
            />
          </div>
        </div>

        {history.isLoading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl bg-surface-2" />
            ))}
          </div>
        ) : history.isError ? (
          <EmptyState
            icon={<History className="h-6 w-6" />}
            title="History unavailable"
            description={history.error.message}
          />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<History className="h-6 w-6" />}
            title={total === 0 ? 'No analyses yet' : 'No matches'}
            description={
              total === 0
                ? 'Completed analyses will appear here.'
                : 'Try a different search or filter.'
            }
            action={total === 0 && <ButtonLink to="/analyze">Start Analysis</ButtonLink>}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <caption className="sr-only">Past analyses</caption>
              <thead className="bg-surface-2 text-xs uppercase tracking-wider text-ink-muted">
                <tr>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Image
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Date
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Prediction
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Type
                  </th>
                  <th scope="col" className="px-4 py-3 text-right font-semibold">
                    Confidence
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Model
                  </th>
                  <th scope="col" className="px-4 py-3">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((h) => (
                  <tr
                    key={h.id}
                    className="cursor-pointer transition-colors hover:bg-surface-2"
                    onClick={() => navigate(`/results/${h.id}`)}
                  >
                    <td className="px-4 py-2.5">
                      <img
                        src={h.thumbnail}
                        alt=""
                        className="h-12 w-12 rounded-lg bg-viewer object-cover"
                      />
                    </td>
                    <td className="px-4 py-2.5">
                      <Link
                        to={`/results/${h.id}`}
                        className="font-medium text-ink hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {dateTime(h.created_at)}
                      </Link>
                      {h.source_name && (
                        <p className="max-w-[16rem] truncate text-xs text-ink-muted">
                          {h.source_name}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <LabelPill label={h.final_label === 'NORMAL' ? 'NORMAL' : 'PNEUMONIA'} />
                    </td>
                    <td className="px-4 py-2.5">
                      {h.final_label === 'NORMAL' ? (
                        <span className="text-ink-muted">—</span>
                      ) : (
                        <LabelPill label={h.final_label} />
                      )}
                    </td>
                    <td className="num px-4 py-2.5 text-right">{pct(h.confidence)}</td>
                    <td className="px-4 py-2.5">
                      <span className="text-ink">{modelText(h)}</span>
                      <span className="mt-0.5 flex gap-1.5">
                        {h.agree === false && (
                          <span className="text-xs text-warning-ink">Models disagree</span>
                        )}
                        {h.is_mock && (
                          <span className="inline-flex items-center gap-1 text-xs text-ink-muted">
                            <FlaskConical className="h-3 w-3" aria-hidden /> mock
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          del.mutate(h.id);
                        }}
                        className="grid h-8 w-8 place-items-center rounded-lg text-ink-muted hover:bg-pneumonia/10 hover:text-pneumonia-ink"
                        aria-label={`Delete analysis from ${dateTime(h.created_at)}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
