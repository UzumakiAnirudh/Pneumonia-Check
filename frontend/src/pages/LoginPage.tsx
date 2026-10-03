import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertOctagon, LogIn, Mail } from 'lucide-react';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { safeNext, useAuth } from '@/features/auth/authStore';
import { TextField } from '@/components/ui/TextField';
import { Button } from '@/components/ui/Button';

export function LoginPage() {
  const { login, status } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = safeNext(params.get('next'));
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === 'authenticated' && !busy) return <Navigate to={next} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Enter your email and password.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to analyse chest X-rays and see your analysis history."
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-pneumonia/40 bg-pneumonia/10 px-3.5 py-3 text-sm text-pneumonia-ink"
          >
            <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            {error}
          </div>
        )}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder="you@hospital.org"
          icon={<Mail className="h-4 w-4" />}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoFocus
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button
          type="submit"
          size="lg"
          className="w-full"
          loading={busy}
          icon={<LogIn className="h-5 w-5" />}
        >
          Log in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-muted">
        New to PneumoScan AI?{' '}
        <Link
          to={`/register${params.get('next') ? `?next=${encodeURIComponent(next)}` : ''}`}
          className="link"
        >
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
