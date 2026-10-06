# Chapter 17 — Frontend code walkthrough

[← Chapter 16](16-backend-walkthrough.md) · [README](../../README.md) · Next: [Chapter 18 →](18-rebuild-from-scratch.md)

The website lives in `frontend/`. Everything below is in `frontend/src/` unless stated otherwise.

---

## 17.1 Configuration files (`frontend/`)

| File                              | Purpose                                                                                                                                               |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `package.json`                    | Libraries and scripts: `dev`, `build`, `lint`, `typecheck`, `test`, `format`                                                                          |
| `vite.config.ts`                  | Dev server on port 5173, the `/api` proxy to the backend (`VITE_PROXY_TARGET`, default `http://localhost:8000`), the `@/` import alias, test settings |
| `tsconfig*.json`                  | TypeScript in strict mode (catches mistakes before running)                                                                                           |
| `tailwind.config.ts`              | Design tokens: colours as CSS variables, fonts (Inter, JetBrains Mono), radii, shadows, the scan animation                                            |
| `eslint.config.js`, `.prettierrc` | Code checks and formatting                                                                                                                            |
| `index.html`                      | The one HTML page; also applies the saved dark/light theme before React starts (no flash)                                                             |
| `.env.example`                    | `VITE_API_BASE_URL` (call a backend on another domain directly) and `VITE_PROXY_TARGET`                                                               |

## 17.2 Start-up

- **`main.tsx`** — renders `<App/>` inside the TanStack Query provider (`api/queryClient.ts`) and Framer
  Motion's config (respects "reduce motion" accessibility settings), and imports the global CSS.
- **`App.tsx`** — the **router**. `/login` and `/register` have their own full-screen layout; all other
  pages sit inside `AppShell`. `/analyze`, `/results`, `/results/:id` and `/history` are wrapped in
  `<RequireAuth>`. The heavy chart page (`PerformancePage`) loads on demand. On start it calls
  `useAuth().bootstrap()` to check whether you are already logged in.

## 17.3 Talking to the backend: `api/`

- **`types.ts`** — TypeScript twins of the backend schemas (`PredictResponse`, `ModelResult`,
  `HealthResponse`, `MetricsResponse`, `AuthUser`, ...) plus the `ApiError` class.
- **`client.ts`** — the `ApiClient` interface (every backend call in one list) and the single `api`
  object used everywhere.
- **`httpClient.ts`** — the implementation with `fetch`: always sends the session cookie
  (`credentials: 'include'`), turns error bodies into readable messages, explains when the website is
  deployed without a backend (HTML instead of JSON, 404/405), and notifies the auth store on **401** so
  an expired session logs you out cleanly.
- **`hooks.ts`** — TanStack Query hooks: `useHealth` (refreshes every 10 s), `useMetrics`,
  `useSamples`, `useHistory`, `useHistoryItem`, `useDeleteHistoryItem`, `useClearHistory`.

## 17.4 Shared state: `store/` and `features/auth/authStore.ts`

- **`settingsStore.ts`** (saved in the browser): theme, default model, confidence threshold
  (default 0.75), history on/off.
- **`analysisStore.ts`** (memory only, for privacy): the selected image, the chosen model, status
  (`validating`, `analyzing`, `rejected`...), validation result, the latest result.
- **`authStore.ts`**: the logged-in user and status (`loading` / `authenticated` / `anonymous`);
  `login`, `register`, `logout` — each clears cached history so nothing from one account is ever shown
  to the next; `safeNext()` only allows same-site redirects after login (prevents "open redirect" tricks).

## 17.5 Layout: `components/layout/`

`AppShell.tsx` draws the sidebar (desktop) or top bar + menu (mobile), the navigation (`nav.ts`), the
**training indicator** (`TrainingStatus.tsx` — live progress when models are being retrained), the
**user menu** (`UserMenu.tsx` — initials, name, email, log-out), the API status dot (`ApiStatus.tsx`,
`useApiStatus.ts`) and the theme toggle.

## 17.6 Pages: `pages/`

| Page                                | What to look at in the code                                                                                                                                                                                                           |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LandingPage.tsx`                   | Hero, feature cards, "how it works", disclaimer                                                                                                                                                                                       |
| `LoginPage.tsx`, `RegisterPage.tsx` | Forms with inline validation; password rules (`features/auth/password.ts`) mirror the backend; layout from `features/auth/AuthLayout.tsx`                                                                                             |
| `AnalyzePage.tsx`                   | Viewer panel with `UploadZone`, `ModelSelector`, `SampleSelector`, image info, privacy notice; the processing view; auto-runs "Compare Models" when sent from the results page                                                        |
| `ResultsPage.tsx`                   | Single-model layout or `ComparisonView`; PDF download (renders the hidden `ReportTemplate`); reopening from history                                                                                                                   |
| `HistoryPage.tsx`                   | Table with search and filters; click to reopen; delete one / all                                                                                                                                                                      |
| `PerformancePage.tsx`               | Internal / External tabs: metric cards, ROC and calibration charts, confusion matrices, comparison table, **performance by population**, training curves, Grad-CAM gallery; shows a warning banner if the data is ever marked as demo |
| `SettingsPage.tsx`                  | Preferences, **model version & training** panel, API status                                                                                                                                                                           |
| `AboutPage.tsx`                     | Project, data, architecture diagrams, Grad-CAM, limitations, team (edit names in `config/project.ts`)                                                                                                                                 |

## 17.7 The analysis flow: `features/analysis/`

- **`useRunAnalysis.ts`** — the heart of the Analyze button: validate → predict, animating the five
  steps (`steps.ts`) on a timer so short requests still feel smooth, then navigates to `/results`.
- **`ProcessingView.tsx`** — the step list and the X-ray with the scanning line.
- **`ExplanationViewer.tsx`** — the dark viewer: modes (original / overlay / heatmap / side by side), the
  opacity slider, legend, R/L markers. The overlay is two stacked images — the X-ray and the heatmap with
  CSS opacity — which is mathematically the same as blending them.
- **`ResultsPanel.tsx`** — Stage 1/2 labels (`components/result/PredictionLabel.tsx`), confidence bars,
  reliability badge (recomputed from _your_ threshold by `utils/reliability.ts`), probability breakdown,
  "What the model looked at", model and timing.
- **`ComparisonView.tsx`** + **`AgreementBanner.tsx`** — the side-by-side view.

## 17.8 Viewer and UI building blocks

- `components/viewer/` — `ZoomPanImage.tsx` + `useZoomPan.ts` (wheel/drag/keyboard zoom and pan),
  `HeatmapLegend.tsx`, `ScanLine.tsx`.
- `components/ui/` — `Button`, `Card`, `Badge`, `SegmentedControl` (keyboard-accessible radio group),
  `Slider`, `Switch`, `Tabs`, `TextField` (with show/hide password), `ConfidenceBar` (an accessible
  `meter`), `Disclaimer`, `EmptyState`, `PageHeader`, `StatusDot`.
- `components/brand/Logo.tsx` — the SVG lungs-with-scan-line logo.
- `features/performance/` — the dashboard's charts (Recharts) and tables.
- `features/report/` — the PDF report (html2canvas + jsPDF).
- `utils/labels.ts` — the single source of truth for how each class looks: text, icon and colour —
  results are **never shown by colour alone** (accessibility for colour-blind users).

## 17.9 Styling and themes

`styles/index.css` defines every colour twice — for light mode (`:root`) and dark mode (`.dark`) — as
CSS variables (clinical blue `#1E5AA8`, cyan accent `#14B8C4`, green Normal, red Pneumonia, orange
Bacterial, violet Viral, amber warnings). Tailwind classes such as `bg-primary` or `text-normal-ink` read
these variables, so switching theme is just toggling the `dark` class on `<html>` (`utils/theme.ts`).
Chart colours were checked for colour-blind safety.

## 17.10 Tests: `__tests__/`

22 Vitest tests: confidence bars and labels, reliability rules, the probability chart, keyboard
navigation of segmented controls, the upload zone (accepts PNG, rejects other types), login redirects,
password rules, the open-redirect guard, and the "backend not connected" messages. Run:
`cd frontend && npm test`.

---

Next: **Chapter 18 — Rebuild everything from scratch** → [18-rebuild-from-scratch.md](18-rebuild-from-scratch.md)
