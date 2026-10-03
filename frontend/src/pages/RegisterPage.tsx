import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertOctagon, Check, Mail, User, UserPlus } from 'lucide-react';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { safeNext, useAuth } from '@/features/auth/authStore';
import { passwordChecks } from '@/features/auth/password';
import { TextField } from '@/components/ui/TextField';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type Errors = Partial<Record<'name' | 'email' | 'password' | 'confirm', string>>;

export function RegisterPage() {
  const { register, status } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = safeNext(params.get('next'));
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [errors, setErrors] = useState<Errors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === 'authenticated' && !busy) return <Navigate to={next} replace />;

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    setErrors((er) => ({ ...er, [k]: undefined }));
  };

  const validate = (): Errors => {
    const er: Errors = {};
    if (!form.name.trim()) er.name = 'Enter your name.';
    if (!EMAIL_RE.test(form.email.trim())) er.email = 'Enter a valid email address.';
    if (!passwordChecks(form.password).every((c) => c.ok))
      er.password = 'Password does not meet the requirements.';
    if (form.confirm !== form.password) er.confirm = 'Passwords do not match.';
    return er;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const er = validate();
    setErrors(er);
    if (Object.keys(er).length) return;
    setBusy(true);
    setServerError(null);
    try {
      await register({ name: form.name.trim(), email: form.email.trim(), password: form.password });
      navigate(next, { replace: true });
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
      setBusy(false);
    }
  };

  const checks = passwordChecks(form.password);

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Each account keeps its own private analysis history."
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {serverError && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-xl border border-pneumonia/40 bg-pneumonia/10 px-3.5 py-3 text-sm text-pneumonia-ink"
          >
            <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            {serverError}
          </div>
        )}
        <TextField
          label="Full name"
          autoComplete="name"
          placeholder="Dr. Jane Doe"
          icon={<User className="h-4 w-4" />}
          value={form.name}
          onChange={set('name')}
          error={errors.name}
          autoFocus
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder="you@hospital.org"
          icon={<Mail className="h-4 w-4" />}
          value={form.email}
          onChange={set('email')}
          error={errors.email}
        />
        <div>
          <TextField
            label="Password"
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={set('password')}
            error={errors.password}
          />
          <ul className="mt-2 space-y-1" aria-label="Password requirements">
            {checks.map((c) => (
              <li
                key={c.label}
                className={cn(
                  'flex items-center gap-1.5 text-xs',
                  c.ok ? 'text-normal-ink' : 'text-ink-muted',
                )}
              >
                <Check
                  className={cn('h-3.5 w-3.5', c.ok ? 'opacity-100' : 'opacity-30')}
                  aria-hidden
                />
                {c.label}
                <span className="sr-only">{c.ok ? '(met)' : '(not met)'}</span>
              </li>
            ))}
          </ul>
        </div>
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          value={form.confirm}
          onChange={set('confirm')}
          error={errors.confirm}
        />
        <Button
          type="submit"
          size="lg"
          className="w-full"
          loading={busy}
          icon={<UserPlus className="h-5 w-5" />}
        >
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-ink-muted">
        Already have an account?{' '}
        <Link
          to={`/login${params.get('next') ? `?next=${encodeURIComponent(next)}` : ''}`}
          className="link"
        >
          Log in
        </Link>
      </p>
    </AuthLayout>
  );
}
