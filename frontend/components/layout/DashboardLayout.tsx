'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Radio,
  Briefcase,
  CheckSquare,
  Mail,
  User,
  BarChart2,
  Settings,
  Zap,
} from 'lucide-react';

const navItems = [
  { href: '/',              label: 'Dashboard',     icon: LayoutDashboard },
  { href: '/signals',       label: 'Signals',       icon: Radio },
  { href: '/opportunities', label: 'Opportunities', icon: Briefcase },
  { href: '/actions',       label: 'Actions',       icon: CheckSquare },
  { href: '/outreach',      label: 'Outreach',      icon: Mail },
  { href: '/profile',       label: 'Profile',       icon: User },
  { href: '/analytics',     label: 'Analytics',     icon: BarChart2 },
  { href: '/settings',      label: 'Settings',      icon: Settings },
];

interface DashboardLayoutProps {
  children: React.ReactNode;
  title?: string;
}

export function DashboardLayout({ children, title }: DashboardLayoutProps) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col bg-gray-950 border-r border-border">
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-5 border-b border-border">
          <div className="flex items-center justify-center w-7 h-7 rounded-md bg-violet-600">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-bold text-foreground tracking-tight">Apex</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
          {navItems.map(({ href, label, icon: Icon }) => {
            const isActive =
              href === '/' ? pathname === '/' : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-violet-600/20 text-violet-300 font-medium'
                    : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                }`}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border">
          <p className="text-[10px] text-muted-foreground">HEC Paris MBA · v1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        {title && (
          <header className="flex items-center h-14 px-6 border-b border-border bg-background flex-shrink-0">
            <h1 className="text-sm font-semibold text-foreground">{title}</h1>
          </header>
        )}

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
