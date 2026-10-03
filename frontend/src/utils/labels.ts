import {
  AlertTriangle,
  Bug,
  CheckCircle2,
  ShieldAlert,
  Virus,
  type LucideIcon,
} from 'lucide-react';
import type { AnyLabel, FinalLabel, ModelKey } from '@/api/types';

export type Tone = 'normal' | 'pneumonia' | 'bacterial' | 'viral' | 'warning';

export interface LabelMeta {
  text: string;
  short: string;
  tone: Tone;
  icon: LucideIcon;
  description: string;
}

/** Single source of truth for how a class is shown: always text + icon + colour. */
export const LABELS: Record<AnyLabel, LabelMeta> = {
  NORMAL: {
    text: 'Normal',
    short: 'NORMAL',
    tone: 'normal',
    icon: CheckCircle2,
    description: 'No radiographic signs of pneumonia detected.',
  },
  PNEUMONIA: {
    text: 'Pneumonia',
    short: 'PNEUMONIA',
    tone: 'pneumonia',
    icon: AlertTriangle,
    description: 'Radiographic patterns consistent with pneumonia detected.',
  },
  BACTERIAL: {
    text: 'Bacterial',
    short: 'BACTERIAL',
    tone: 'bacterial',
    icon: Bug,
    description:
      'Pattern more consistent with bacterial pneumonia (e.g. focal lobar consolidation).',
  },
  VIRAL: {
    text: 'Viral',
    short: 'VIRAL',
    tone: 'viral',
    icon: Virus,
    description:
      'Pattern more consistent with viral pneumonia (e.g. diffuse, bilateral interstitial).',
  },
};

export const WARNING_ICON = ShieldAlert;

/** Static class strings so Tailwind can see them. */
export const TONE_CLASSES: Record<
  Tone,
  { text: string; bg: string; soft: string; border: string; fill: string }
> = {
  normal: {
    text: 'text-normal-ink',
    bg: 'bg-normal',
    soft: 'bg-normal/10',
    border: 'border-normal/40',
    fill: 'fill-normal',
  },
  pneumonia: {
    text: 'text-pneumonia-ink',
    bg: 'bg-pneumonia',
    soft: 'bg-pneumonia/10',
    border: 'border-pneumonia/40',
    fill: 'fill-pneumonia',
  },
  bacterial: {
    text: 'text-bacterial-ink',
    bg: 'bg-bacterial',
    soft: 'bg-bacterial/10',
    border: 'border-bacterial/40',
    fill: 'fill-bacterial',
  },
  viral: {
    text: 'text-viral-ink',
    bg: 'bg-viral',
    soft: 'bg-viral/10',
    border: 'border-viral/40',
    fill: 'fill-viral',
  },
  warning: {
    text: 'text-warning-ink',
    bg: 'bg-warning',
    soft: 'bg-warning/10',
    border: 'border-warning/50',
    fill: 'fill-warning',
  },
};

/** Hex values for charts (SVG/canvas can't use Tailwind classes). */
export const TONE_HEX: Record<Tone, string> = {
  normal: '#22A06B',
  pneumonia: '#D64545',
  bacterial: '#E07B24',
  viral: '#7A5AF8',
  warning: '#E0A800',
};

export const MODEL_META: Record<
  ModelKey,
  { name: string; short: string; family: string; color: string }
> = {
  densenet: { name: 'DenseNet121', short: 'DenseNet', family: 'CNN', color: '#1E5AA8' },
  swin: { name: 'Swin Transformer', short: 'Swin', family: 'Vision Transformer', color: '#14B8C4' },
};

export const FINAL_LABELS: FinalLabel[] = ['NORMAL', 'BACTERIAL', 'VIRAL'];
