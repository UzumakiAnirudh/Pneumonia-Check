import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ModelChoice } from '@/api/types';

export type ThemePreference = 'light' | 'dark' | 'system';

export interface SettingsState {
  theme: ThemePreference;
  defaultModel: ModelChoice;
  /** Below this calibrated confidence a result is flagged for expert review. */
  confidenceThreshold: number;
  historyEnabled: boolean;
  setTheme: (theme: ThemePreference) => void;
  setDefaultModel: (model: ModelChoice) => void;
  setConfidenceThreshold: (value: number) => void;
  setHistoryEnabled: (value: boolean) => void;
}

export const DEFAULT_THRESHOLD = 0.75;

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'system',
      defaultModel: 'densenet',
      confidenceThreshold: DEFAULT_THRESHOLD,
      historyEnabled: true,
      setTheme: (theme) => set({ theme }),
      setDefaultModel: (defaultModel) => set({ defaultModel }),
      setConfidenceThreshold: (confidenceThreshold) =>
        set({ confidenceThreshold: Math.min(0.99, Math.max(0.5, confidenceThreshold)) }),
      setHistoryEnabled: (historyEnabled) => set({ historyEnabled }),
    }),
    { name: 'pneumoscan-settings', version: 1 },
  ),
);
