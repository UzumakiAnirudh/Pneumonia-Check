import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import { queryKeys } from '@/api/hooks';
import { ApiError, type ModelChoice } from '@/api/types';
import { useAnalysis } from '@/store/analysisStore';
import { useSettings } from '@/store/settingsStore';
import { PROCESSING_STEPS } from './steps';

const STEP_MS = 520;
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Drives validate → predict and the visual step indicator. Steps after validation
 * advance on a timer while the request is in flight, then complete together.
 */
export function useRunAnalysis() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { setStatus, setValidation, setResult, setError, setModel } = useAnalysis();
  const threshold = useSettings((s) => s.confidenceThreshold);
  const historyEnabled = useSettings((s) => s.historyEnabled);
  const [step, setStep] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval>>();
  // Set in the effect body (not just on first render) so StrictMode's mount/unmount/mount
  // cycle in development leaves it true.
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      clearInterval(timer.current);
    };
  }, []);

  const run = useCallback(
    async (model: ModelChoice) => {
      const image = useAnalysis.getState().image;
      if (!image) return;
      setModel(model);
      setError(null);
      setStep(0);
      setStatus('validating');
      try {
        const [validation] = await Promise.all([api.validate(image.file), wait(STEP_MS)]);
        if (!mounted.current) return;
        setValidation(validation);
        if (!validation.is_valid) {
          setStatus('rejected');
          return;
        }
        setStatus('analyzing');
        setStep(1);
        timer.current = setInterval(() => {
          setStep((s) => Math.min(s + 1, PROCESSING_STEPS.length - 1));
        }, STEP_MS);
        const [result] = await Promise.all([
          api.predict({
            file: image.file,
            model,
            threshold,
            saveHistory: historyEnabled,
            sourceName: image.sourceName ?? image.file.name,
          }),
          wait(STEP_MS * (PROCESSING_STEPS.length - 1)),
        ]);
        clearInterval(timer.current);
        if (!mounted.current) return;
        setStep(PROCESSING_STEPS.length);
        await wait(300);
        setResult(result);
        setStatus('done');
        if (result.saved_to_history) qc.invalidateQueries({ queryKey: queryKeys.history });
        navigate('/results');
      } catch (err) {
        clearInterval(timer.current);
        if (!mounted.current) return;
        if (err instanceof ApiError && err.detail.validation) {
          setValidation(err.detail.validation);
          setStatus('rejected');
          return;
        }
        setError(err instanceof Error ? err.message : 'Analysis failed. Please try again.');
        setStatus('error');
      }
    },
    [
      historyEnabled,
      navigate,
      qc,
      setError,
      setModel,
      setResult,
      setStatus,
      setValidation,
      threshold,
    ],
  );

  return { run, step };
}
