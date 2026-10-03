import type { ModelResult, Reliability } from '@/api/types';

/**
 * Recomputes reliability against the user's current threshold, so changing the
 * setting re-evaluates results (including ones reopened from history).
 * A result is "high confidence" only if every stage that ran clears the threshold.
 */
export function getReliability(result: ModelResult, threshold: number): Reliability {
  const confidences = [result.stage1.confidence, result.stage2?.confidence].filter(
    (c): c is number => typeof c === 'number',
  );
  const weakest = Math.min(...confidences);
  return weakest >= threshold
    ? { level: 'high', threshold, message: 'High confidence' }
    : { level: 'low', threshold, message: 'Low confidence — recommend expert review' };
}
