import { useNavigate } from 'react-router-dom';
import { LogIn, LogOut, UserPlus } from 'lucide-react';
import { useAuth } from '@/features/auth/authStore';
import { ButtonLink } from '@/components/ui/Button';
import { cn } from '@/utils/cn';

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('');
}

/** Signed-in account with a logout button, or log-in / register links. */
export function UserMenu({
  className,
  onNavigate,
}: {
  className?: string;
  onNavigate?: () => void;
}) {
  const { user, status, logout } = useAuth();
  const navigate = useNavigate();

  if (status === 'loading')
    return <div className={cn('h-11 animate-pulse rounded-xl bg-surface-2', className)} />;

  if (!user) {
    return (
      <div className={cn('flex gap-2', className)}>
        <ButtonLink
          to="/login"
          size="sm"
          className="flex-1"
          icon={<LogIn className="h-4 w-4" />}
          onClick={onNavigate}
        >
          Log in
        </ButtonLink>
        <ButtonLink
          to="/register"
          size="sm"
          variant="outline"
          className="flex-1"
          icon={<UserPlus className="h-4 w-4" />}
          onClick={onNavigate}
        >
          Register
        </ButtonLink>
      </div>
    );
  }

  return (
    <div className={cn('flex items-center gap-2.5 rounded-xl bg-surface-2 p-2', className)}>
      <span
        className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary text-sm font-semibold text-white"
        aria-hidden
      >
        {initials(user.name) || '?'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">{user.name}</p>
        <p className="truncate text-xs text-ink-muted">{user.email}</p>
      </div>
      <button
        type="button"
        onClick={async () => {
          onNavigate?.();
          await logout();
          navigate('/login');
        }}
        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-ink-muted hover:bg-surface hover:text-pneumonia-ink"
        aria-label={`Log out ${user.name}`}
        title="Log out"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}
