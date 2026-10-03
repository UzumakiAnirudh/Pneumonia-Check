import type { ModelResult } from '@/api/types';

export function makeResult(overrides: Partial<ModelResult> = {}): ModelResult {
  return {
    model: 'densenet',
    model_name: 'DenseNet121',
    mode: 'two_stage',
    stage1: {
      label: 'PNEUMONIA',
      confidence: 0.92,
      probabilities: { NORMAL: 0.08, PNEUMONIA: 0.92 },
      temperature: 1.2,
    },
    stage2: {
      label: 'BACTERIAL',
      confidence: 0.81,
      probabilities: { BACTERIAL: 0.81, VIRAL: 0.19 },
      temperature: 1.1,
    },
    final_label: 'BACTERIAL',
    final_confidence: 0.745,
    class_probabilities: { NORMAL: 0.08, BACTERIAL: 0.745, VIRAL: 0.175 },
    reliability: { level: 'high', threshold: 0.75, message: 'High confidence' },
    explanation: null,
    inference_ms: 120,
    ...overrides,
  };
}
