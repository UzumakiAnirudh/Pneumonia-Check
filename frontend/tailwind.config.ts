import type { Config } from 'tailwindcss';

/** Colours are CSS variables (RGB channels) so light/dark themes swap at runtime
 *  and Tailwind opacity modifiers (`bg-primary/10`) keep working. */
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: token('bg'),
        surface: { DEFAULT: token('surface'), 2: token('surface-2') },
        border: token('border'),
        ink: { DEFAULT: token('text'), muted: token('text-muted') },
        primary: {
          DEFAULT: token('primary'),
          light: token('primary-light'),
          text: token('primary-text'),
        },
        accent: token('accent'),
        viewer: { DEFAULT: token('viewer'), panel: token('viewer-panel'), line: token('viewer-line') },
        normal: { DEFAULT: token('normal'), ink: token('normal-ink') },
        pneumonia: { DEFAULT: token('pneumonia'), ink: token('pneumonia-ink') },
        bacterial: { DEFAULT: token('bacterial'), ink: token('bacterial-ink') },
        viral: { DEFAULT: token('viral'), ink: token('viral-ink') },
        warning: { DEFAULT: token('warning'), ink: token('warning-ink') },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        body: ['0.9375rem', { lineHeight: '1.6' }],
        label: ['2.5rem', { lineHeight: '1.1', fontWeight: '700' }],
      },
      borderRadius: { card: '16px' },
      boxShadow: {
        soft: '0 1px 2px rgb(16 24 40 / 0.04), 0 4px 16px rgb(16 24 40 / 0.06)',
        lift: '0 2px 4px rgb(16 24 40 / 0.06), 0 12px 32px rgb(16 24 40 / 0.10)',
        glow: '0 0 0 1px rgb(var(--accent) / 0.4), 0 0 24px rgb(var(--accent) / 0.25)',
      },
      keyframes: {
        scan: {
          '0%': { top: '0%', opacity: '0' },
          '8%': { opacity: '1' },
          '92%': { opacity: '1' },
          '100%': { top: '100%', opacity: '0' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.9)', opacity: '0.7' },
          '100%': { transform: 'scale(1.6)', opacity: '0' },
        },
      },
      animation: {
        scan: 'scan 2.2s cubic-bezier(0.45, 0, 0.55, 1) infinite',
        'pulse-ring': 'pulse-ring 1.6s ease-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config;
