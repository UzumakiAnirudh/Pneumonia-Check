import { create } from 'zustand';
import type { ModelChoice, PredictResponse, ValidationResult } from '@/api/types';

export type AnalysisStatus = 'idle' | 'validating' | 'analyzing' | 'done' | 'rejected' | 'error';

export interface SelectedImage {
  file: File;
  /** Object URL for previews; revoked when replaced. */
  previewUrl: string | null;
  sourceName: string | null;
  width: number | null;
  height: number | null;
}

interface AnalysisState {
  image: SelectedImage | null;
  model: ModelChoice | null;
  status: AnalysisStatus;
  validation: ValidationResult | null;
  result: PredictResponse | null;
  error: string | null;
  setImage: (image: SelectedImage | null) => void;
  setModel: (model: ModelChoice) => void;
  setStatus: (status: AnalysisStatus) => void;
  setValidation: (validation: ValidationResult | null) => void;
  setResult: (result: PredictResponse | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

/** Session-only state for the current analysis. Never persisted (privacy). */
export const useAnalysis = create<AnalysisState>()((set, get) => ({
  image: null,
  model: null,
  status: 'idle',
  validation: null,
  result: null,
  error: null,
  setImage: (image) => {
    const prev = get().image?.previewUrl;
    if (prev && prev !== image?.previewUrl) URL.revokeObjectURL(prev);
    set({ image, status: 'idle', validation: null, error: null });
  },
  setModel: (model) => set({ model }),
  setStatus: (status) => set({ status }),
  setValidation: (validation) => set({ validation }),
  setResult: (result) => set({ result }),
  setError: (error) => set({ error }),
  reset: () => {
    const prev = get().image?.previewUrl;
    if (prev) URL.revokeObjectURL(prev);
    set({ image: null, status: 'idle', validation: null, result: null, error: null });
  },
}));
