'use client';

import { cn } from '@/lib/utils';
import { Phone, Eye, Pause, MoreVertical } from 'lucide-react';
import { VoiceVisualizer } from '@/components/ui/voice-visualizer';
import { useState, useEffect } from 'react';

interface LiveCall {
  id: string;
  phoneNumber: string;
  customerName: string;
  campaignName: string;
  duration: number;
  status: 'ringing' | 'connected' | 'talking' | 'on-hold';
  audioLevel: number;
}

// Mock data
const mockCalls: LiveCall[] = [
  {
    id: '1',
    phoneNumber: '+90 532 XXX XX 12',
    customerName: 'John Smith',
    campaignName: 'Payment Reminder',
    duration: 154,
    status: 'talking',
    audioLevel: 0.7,
  },
  {
    id: '2',
    phoneNumber: '+90 535 XXX XX 45',
    customerName: 'Jane Doe',
    campaignName: 'Payment Reminder',
    duration: 45,
    status: 'connected',
    audioLevel: 0.3,
  },
  {
    id: '3',
    phoneNumber: '+90 542 XXX XX 78',
    customerName: 'Michael Brown',
    campaignName: 'Survey',
    duration: 12,
    status: 'ringing',
    audioLevel: 0,
  },
  {
    id: '4',
    phoneNumber: '+90 553 XXX XX 90',
    customerName: 'Emily Johnson',
    campaignName: 'Payment Reminder',
    duration: 89,
    status: 'talking',
    audioLevel: 0.5,
  },
];

export function LiveCallsWidget() {
  const [calls, setCalls] = useState<LiveCall[]>(mockCalls);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setCalls((prev) =>
        prev.map((call) => ({
          ...call,
          duration: call.status !== 'ringing' ? call.duration + 1 : call.duration,
          audioLevel:
            call.status === 'talking'
              ? Math.min(1, Math.max(0, call.audioLevel + (Math.random() - 0.5) * 0.3))
              : call.audioLevel,
        }))
      );
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const statusColors = {
    ringing: 'bg-warning-500',
    connected: 'bg-success-500',
    talking: 'bg-primary-500',
    'on-hold': 'bg-muted-foreground',
  };

  const statusLabels = {
    ringing: 'Ringing',
    connected: 'Connected',
    talking: 'AI Talking',
    'on-hold': 'On Hold',
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/10">
            <Phone className="h-5 w-5 text-primary-500" />
          </div>
          <div>
            <h3 className="font-semibold">Live Calls</h3>
            <p className="text-sm text-muted-foreground">
              {calls.length} active calls
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-error-500/10 text-error-500 text-sm font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-error-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-error-500" />
            </span>
            LIVE
          </span>
        </div>
      </div>

      {/* Calls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {calls.map((call) => (
          <div
            key={call.id}
            className={cn(
              'relative p-4 rounded-xl border border-border',
              'bg-background hover:bg-muted/50 transition-colors',
              'group'
            )}
          >
            {/* Status indicator line */}
            <div
              className={cn(
                'absolute left-0 top-4 bottom-4 w-1 rounded-r-full',
                statusColors[call.status]
              )}
            />

            <div className="pl-3">
              {/* Top row */}
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-medium">{call.customerName}</p>
                  <p className="text-sm text-muted-foreground">{call.phoneNumber}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded-full text-xs font-medium',
                      call.status === 'ringing' && 'bg-warning-500/10 text-warning-500',
                      call.status === 'connected' && 'bg-success-500/10 text-success-500',
                      call.status === 'talking' && 'bg-primary-500/10 text-primary-500',
                      call.status === 'on-hold' && 'bg-muted text-muted-foreground'
                    )}
                  >
                    {statusLabels[call.status]}
                  </span>
                </div>
              </div>

              {/* Voice visualizer */}
              <div className="h-12 mb-3">
                <VoiceVisualizer
                  mode="bars"
                  isActive={call.status === 'talking'}
                  audioLevel={call.audioLevel}
                  size="sm"
                  className="h-full w-full"
                />
              </div>

              {/* Bottom row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    {call.campaignName}
                  </span>
                  <span className="text-muted-foreground">•</span>
                  <span className="text-sm font-mono font-medium">
                    {formatDuration(call.duration)}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg',
                      'hover:bg-muted transition-colors'
                    )}
                    title="Monitor call"
                  >
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <button
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg',
                      'hover:bg-muted transition-colors'
                    )}
                    title="Hold call"
                  >
                    <Pause className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <button
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg',
                      'hover:bg-muted transition-colors'
                    )}
                  >
                    <MoreVertical className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* View all link */}
      <div className="mt-4 text-center">
        <a
          href="/dashboard/calls/live"
          className="text-sm text-primary-500 hover:text-primary-600 font-medium"
        >
          View all active calls →
        </a>
      </div>
    </div>
  );
}
