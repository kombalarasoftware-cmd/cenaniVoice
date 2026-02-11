'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Bot,
  Megaphone,
  Phone,
  FileAudio,
  PhoneCall,
  BarChart3,
  Settings,
  ChevronLeft,
  Moon,
  Sun,
  LogOut,
  User,
  CalendarCheck,
  UserPlus,
  ClipboardList,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import { useState, useEffect } from 'react';

const navigation = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Agents',
    href: '/dashboard/agents',
    icon: Bot,
  },
  {
    name: 'Campaigns',
    href: '/dashboard/campaigns',
    icon: Megaphone,
  },
  {
    name: 'Numbers',
    href: '/dashboard/numbers',
    icon: Phone,
  },
  {
    name: 'Recordings',
    href: '/dashboard/recordings',
    icon: FileAudio,
  },
  {
    name: 'Call Logs',
    href: '/dashboard/call-logs',
    icon: PhoneCall,
  },
  {
    name: 'Appointments',
    href: '/dashboard/appointments',
    icon: CalendarCheck,
  },
  {
    name: 'Leads',
    href: '/dashboard/leads',
    icon: UserPlus,
  },
  {
    name: 'Surveys',
    href: '/dashboard/surveys',
    icon: ClipboardList,
  },
  {
    name: 'Reports',
    href: '/dashboard/reports',
    icon: BarChart3,
  },
];

const bottomNavigation = [
  {
    name: 'Settings',
    href: '/dashboard/settings',
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [userName, setUserName] = useState('User');
  const [userEmail, setUserEmail] = useState('');

  useEffect(() => {
    try {
      const name = localStorage.getItem('user_name');
      const email = localStorage.getItem('user_email');
      if (name) setUserName(name);
      if (email) setUserEmail(email);
    } catch {
      // localStorage unavailable
    }
  }, []);

  const handleLogout = async () => {
    // Attempt server-side token invalidation
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    } catch {
      // Continue with client-side cleanup even if server logout fails
    }

    // Clear all stored data + cookies
    localStorage.clear();
    document.cookie = 'access_token=; path=/; max-age=0';
    document.cookie = 'refresh_token=; path=/; max-age=0';
    router.push('/login');
  };

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen transition-all duration-300 ease-in-out',
        'bg-background border-r border-border',
        collapsed ? 'w-[72px]' : 'w-64'
      )}
    >
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-border">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-secondary-500">
              <Bot className="h-6 w-6 text-white" />
            </div>
            {!collapsed && (
              <span className="font-semibold text-lg gradient-text">VoiceAI</span>
            )}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg',
              'hover:bg-muted transition-colors',
              collapsed && 'absolute -right-4 top-6 bg-background border border-border shadow-sm'
            )}
          >
            <ChevronLeft
              className={cn(
                'h-4 w-4 transition-transform',
                collapsed && 'rotate-180'
              )}
            />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-3 overflow-y-auto custom-scrollbar">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200',
                  'hover:bg-muted group relative',
                  isActive && 'bg-primary-500/10 text-primary-500',
                  !isActive && 'text-muted-foreground hover:text-foreground'
                )}
              >
                {/* Active indicator */}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary-500 rounded-r-full" />
                )}
                
                <item.icon
                  className={cn(
                    'h-5 w-5 flex-shrink-0 transition-colors',
                    isActive ? 'text-primary-500' : 'text-muted-foreground group-hover:text-foreground'
                  )}
                />
                
                {!collapsed && (
                  <span className="flex-1 font-medium">{item.name}</span>
                )}

                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-sm rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                    {item.name}
                  </div>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="border-t border-border p-3 space-y-1">
          {/* Theme toggle */}
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className={cn(
              'flex w-full items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200',
              'hover:bg-muted text-muted-foreground hover:text-foreground group relative'
            )}
          >
            {theme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
            {!collapsed && (
              <span className="font-medium">
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </span>
            )}
            {collapsed && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-sm rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
              </div>
            )}
          </button>

          {/* Settings */}
          {bottomNavigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200',
                  'hover:bg-muted group relative',
                  isActive && 'bg-primary-500/10 text-primary-500',
                  !isActive && 'text-muted-foreground hover:text-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
                {!collapsed && <span className="font-medium">{item.name}</span>}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-sm rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
                    {item.name}
                  </div>
                )}
              </Link>
            );
          })}

          {/* User profile with logout dropdown */}
          <div className="relative mt-2">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className={cn(
                'flex w-full items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200',
                'bg-muted/50 hover:bg-muted cursor-pointer'
              )}
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-primary-400 to-secondary-400 flex-shrink-0">
                <User className="h-5 w-5 text-white" />
              </div>
              {!collapsed && (
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-sm font-medium truncate">{userName}</p>
                  <p className="text-xs text-muted-foreground truncate">{userEmail}</p>
                </div>
              )}
            </button>

            {/* Logout popup */}
            {showUserMenu && (
              <div className={cn(
                'absolute bottom-full mb-2 rounded-xl border border-border bg-popover shadow-xl p-1 z-50',
                collapsed ? 'left-full ml-2' : 'left-0 right-0'
              )}>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-3 px-3 py-2.5 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="text-sm font-medium">Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
