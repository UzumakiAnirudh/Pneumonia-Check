import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, Moon, Sun, X } from 'lucide-react';
import { Logo } from '@/components/brand/Logo';
import { NAV_ITEMS } from './nav';
import { ApiStatus } from './ApiStatus';
import { UserMenu } from './UserMenu';
import { useSettings } from '@/store/settingsStore';
import { useIsDark } from '@/utils/theme';
import { cn } from '@/utils/cn';

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="space-y-1">
      {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors',
                isActive
                  ? 'bg-primary-light text-primary-text'
                  : 'text-ink-muted hover:bg-surface-2 hover:text-ink',
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn('h-[18px] w-[18px]', isActive && 'text-accent')} aria-hidden />
                {label}
              </>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function ThemeToggle() {
  const setTheme = useSettings((s) => s.setTheme);
  const dark = useIsDark();
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      className="grid h-9 w-9 place-items-center rounded-xl text-ink-muted hover:bg-surface-2 hover:text-ink"
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {dark ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
    </button>
  );
}

export function AppShell() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setOpen(false);
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  return (
    <div className="min-h-screen lg:pl-64">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:shadow-lift"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-surface lg:flex">
        <div className="flex h-16 items-center px-5">
          <NavLink to="/" aria-label="PneumoScan AI home">
            <Logo />
          </NavLink>
        </div>
        <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-4">
          <NavList />
        </nav>
        <div className="space-y-3 border-t border-border px-3 py-3">
          <UserMenu />
          <div className="flex items-center justify-between px-1">
            <ApiStatus />
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-surface/90 px-4 backdrop-blur lg:hidden">
        <NavLink to="/" aria-label="PneumoScan AI home">
          <Logo />
        </NavLink>
        <div className="flex items-center gap-1">
          <ThemeToggle />
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-xl text-ink hover:bg-surface-2"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? 'Close menu' : 'Open menu'}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </header>
      <AnimatePresence>
        {open && (
          <motion.nav
            id="mobile-nav"
            aria-label="Main"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-x-0 top-14 z-20 border-b border-border bg-surface px-3 pb-4 pt-2 shadow-lift lg:hidden"
          >
            <NavList onNavigate={() => setOpen(false)} />
            <UserMenu className="mt-3" onNavigate={() => setOpen(false)} />
            <ApiStatus className="mt-3 px-3" />
          </motion.nav>
        )}
      </AnimatePresence>

      <main id="main" className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <Outlet />
      </main>
    </div>
  );
}
