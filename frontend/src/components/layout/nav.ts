import { BarChart3, History, Home, Info, ScanLine, Settings, type LucideIcon } from 'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Home', icon: Home, end: true },
  { to: '/analyze', label: 'Analyze', icon: ScanLine },
  { to: '/performance', label: 'Model Performance', icon: BarChart3 },
  { to: '/history', label: 'History', icon: History },
  { to: '/about', label: 'About', icon: Info },
  { to: '/settings', label: 'Settings', icon: Settings },
];
