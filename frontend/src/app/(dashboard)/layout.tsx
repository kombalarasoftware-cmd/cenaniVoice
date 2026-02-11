'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/layout/sidebar';
import { CallProvider } from '@/components/providers/call-provider';
import { FloatingCallWidget } from '@/components/call/floating-call-widget';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.replace('/login');
      return;
    }

    // Validate token structure and expiry
    try {
      const parts = token.split('.');
      if (parts.length !== 3) throw new Error('Invalid JWT');
      const payload = JSON.parse(atob(parts[1]));
      if (payload.exp && payload.exp * 1000 < Date.now()) {
        localStorage.removeItem('access_token');
        router.replace('/login');
        return;
      }
      setIsAuthenticated(true);
      setIsLoading(false);
    } catch {
      localStorage.removeItem('access_token');
      router.replace('/login');
    }
  }, [router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <CallProvider>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="pl-64">
          {children}
        </main>
        <FloatingCallWidget />
      </div>
    </CallProvider>
  );
}
