import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from './authStore';

/** Gate for pages that need an account; remembers where the user was going. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuth((s) => s.status);
  const location = useLocation();
  if (status === 'loading') {
    return (
      <div className="flex h-64 items-center justify-center text-ink-muted" role="status">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" aria-hidden /> Checking your session…
      </div>
    );
  }
  if (status === 'anonymous') {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <>{children}</>;
}
