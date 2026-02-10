'use client';

import { Bell, Search, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';

interface HeaderProps {
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function Header({ title, description, action }: HeaderProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const handleSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      router.push(`/dashboard/call-logs?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-lg border-b border-border">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Left: Title */}
        <div>
          <h1 className="text-xl font-semibold">{title}</h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
              className={cn(
                'h-9 w-64 rounded-lg bg-muted/50 pl-9 pr-4 text-sm',
                'border border-transparent focus:border-primary-500 focus:bg-background',
                'outline-none transition-all duration-200',
                'placeholder:text-muted-foreground'
              )}
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground">
              Enter
            </kbd>
          </div>

          {/* Notifications */}
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className={cn(
                'relative flex h-9 w-9 items-center justify-center rounded-lg',
                'hover:bg-muted transition-colors'
              )}
            >
              <Bell className="h-5 w-5 text-muted-foreground" />
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-error-500" />
            </button>

            {showNotifications && (
              <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-border bg-popover shadow-xl z-50">
                <div className="p-4 border-b border-border">
                  <h3 className="font-semibold text-sm">Notifications</h3>
                </div>
                <div className="p-6 text-center">
                  <Bell className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No new notifications</p>
                </div>
              </div>
            )}
          </div>

          {/* Primary action */}
          {action && (
            <button
              onClick={action.onClick}
              className={cn(
                'flex h-9 items-center gap-2 px-4 rounded-lg',
                'bg-primary-500 hover:bg-primary-600 text-white',
                'font-medium text-sm transition-colors'
              )}
            >
              <Plus className="h-4 w-4" />
              {action.label}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
