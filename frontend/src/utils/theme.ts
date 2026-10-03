import { useEffect, useState } from 'react';
import { useSettings } from '@/store/settingsStore';
import type { ModelKey } from '@/api/types';

function systemPrefersDark() {
  return (
    typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches
  );
}

/** Resolves the theme preference and keeps the <html> class in sync. */
export function useApplyTheme() {
  const theme = useSettings((s) => s.theme);
  useEffect(() => {
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && systemPrefersDark());
      document.documentElement.classList.toggle('dark', Boolean(dark));
    };
    apply();
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, [theme]);
}

export function useIsDark(): boolean {
  const theme = useSettings((s) => s.theme);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  useEffect(() => {
    const update = () => setDark(document.documentElement.classList.contains('dark'));
    update();
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, [theme]);
  return dark;
}

/**
 * Chart colours. Model series were checked with the dataviz palette validator
 * (CVD + normal-vision separation, lightness band) for each surface.
 */
export function useChartTheme() {
  const dark = useIsDark();
  const series: Record<ModelKey, string> = dark
    ? { densenet: '#3F78D6', swin: '#14A3AD' }
    : { densenet: '#1E5AA8', swin: '#14B8C4' };
  return {
    dark,
    series,
    grid: dark ? '#25324A' : '#E3E9F0',
    axis: dark ? '#96A2B7' : '#5B6678',
    text: dark ? '#E4EAF2' : '#1A2333',
    surface: dark ? '#111929' : '#FFFFFF',
    chance: dark ? '#56627A' : '#A9B3C2',
  };
}
