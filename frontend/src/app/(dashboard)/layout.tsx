'use client';

import { Sidebar } from '@/components/layout/sidebar';
import { CallProvider } from '@/components/providers/call-provider';
import { FloatingCallWidget } from '@/components/call/floating-call-widget';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
