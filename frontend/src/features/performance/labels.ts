import type { MetricSummary } from '@/api/types';

export const METRIC_LABELS: Record<keyof MetricSummary, { label: string; hint: string }> = {
  accuracy: { label: 'Accuracy', hint: 'Share of all predictions that are correct' },
  precision: { label: 'Precision', hint: 'Of predicted positives, how many are truly positive' },
  recall: { label: 'Recall (sensitivity)', hint: 'Of true positives, how many were found' },
  specificity: {
    label: 'Specificity',
    hint: 'Of true negatives, how many were correctly ruled out',
  },
  f1: { label: 'F1-score', hint: 'Harmonic mean of precision and recall' },
  roc_auc: { label: 'ROC-AUC', hint: 'Ranking quality across all thresholds' },
};

export const TASK_LABELS: Record<string, string> = {
  stage1: 'Stage 1 · Normal vs Pneumonia',
  stage2: 'Stage 2 · Bacterial vs Viral',
  pipeline: 'Two-stage pipeline · 3 classes (macro)',
  three_class: 'Single 3-class model (macro)',
};
