import { lazy, Suspense, useEffect } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { LandingPage } from '@/pages/LandingPage';
import { AnalyzePage } from '@/pages/AnalyzePage';
import { ResultsPage } from '@/pages/ResultsPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { AboutPage } from '@/pages/AboutPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { RequireAuth } from '@/features/auth/RequireAuth';
import { useAuth } from '@/features/auth/authStore';
import { useApplyTheme } from '@/utils/theme';

// Recharts is heavy; load the dashboard on demand.
const PerformancePage = lazy(() => import('@/pages/PerformancePage'));

function PageFallback() {
  return <div className="h-64 animate-pulse rounded-card bg-surface-2" aria-label="Loading" />;
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <LandingPage /> },
      {
        path: '/analyze',
        element: (
          <RequireAuth>
            <AnalyzePage />
          </RequireAuth>
        ),
      },
      {
        path: '/results',
        element: (
          <RequireAuth>
            <ResultsPage />
          </RequireAuth>
        ),
      },
      {
        path: '/results/:id',
        element: (
          <RequireAuth>
            <ResultsPage />
          </RequireAuth>
        ),
      },
      {
        path: '/performance',
        element: (
          <Suspense fallback={<PageFallback />}>
            <PerformancePage />
          </Suspense>
        ),
      },
      {
        path: '/history',
        element: (
          <RequireAuth>
            <HistoryPage />
          </RequireAuth>
        ),
      },
      { path: '/about', element: <AboutPage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export default function App() {
  useApplyTheme();
  const bootstrap = useAuth((s) => s.bootstrap);
  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);
  return <RouterProvider router={router} />;
}
