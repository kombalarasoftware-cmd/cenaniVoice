'use client';

import { cn } from '@/lib/utils';
import { Megaphone, Play, Pause, MoreVertical } from 'lucide-react';

interface Campaign {
  id: string;
  name: string;
  progress: number;
  status: 'running' | 'paused' | 'completed' | 'draft';
  totalCalls: number;
  completedCalls: number;
  activeCalls: number;
}

const mockCampaigns: Campaign[] = [
  {
    id: '1',
    name: 'Ödeme Hatırlatma - Ocak',
    progress: 67,
    status: 'running',
    totalCalls: 5000,
    completedCalls: 3350,
    activeCalls: 12,
  },
  {
    id: '2',
    name: 'Müşteri Memnuniyet Anketi',
    progress: 100,
    status: 'completed',
    totalCalls: 2000,
    completedCalls: 2000,
    activeCalls: 0,
  },
  {
    id: '3',
    name: 'Yeni Ürün Tanıtımı',
    progress: 34,
    status: 'paused',
    totalCalls: 3000,
    completedCalls: 1020,
    activeCalls: 0,
  },
  {
    id: '4',
    name: 'Randevu Hatırlatma',
    progress: 89,
    status: 'running',
    totalCalls: 500,
    completedCalls: 445,
    activeCalls: 5,
  },
];

export function CampaignProgress() {
  const statusConfig = {
    running: {
      label: 'Running',
      color: 'text-success-500',
      bg: 'bg-success-500/10',
      barColor: 'bg-success-500',
    },
    paused: {
      label: 'Paused',
      color: 'text-warning-500',
      bg: 'bg-warning-500/10',
      barColor: 'bg-warning-500',
    },
    completed: {
      label: 'Completed',
      color: 'text-primary-500',
      bg: 'bg-primary-500/10',
      barColor: 'bg-primary-500',
    },
    draft: {
      label: 'Draft',
      color: 'text-muted-foreground',
      bg: 'bg-muted',
      barColor: 'bg-muted-foreground',
    },
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary-500/10">
            <Megaphone className="h-5 w-5 text-secondary-500" />
          </div>
          <div>
            <h3 className="font-semibold">Campaign Progress</h3>
            <p className="text-sm text-muted-foreground">
              {mockCampaigns.filter((c) => c.status === 'running').length} active campaigns
            </p>
          </div>
        </div>
        <a
          href="/dashboard/campaigns"
          className="text-sm text-primary-500 hover:text-primary-600 font-medium"
        >
          View all →
        </a>
      </div>

      {/* Campaign list */}
      <div className="space-y-4">
        {mockCampaigns.map((campaign) => (
          <div
            key={campaign.id}
            className={cn(
              'p-4 rounded-xl border border-border',
              'hover:bg-muted/50 transition-colors group'
            )}
          >
            {/* Top row */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{campaign.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={cn(
                      'px-2 py-0.5 rounded-full text-xs font-medium',
                      statusConfig[campaign.status].bg,
                      statusConfig[campaign.status].color
                    )}
                  >
                    {statusConfig[campaign.status].label}
                  </span>
                  {campaign.activeCalls > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {campaign.activeCalls} active
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {campaign.status === 'running' ? (
                  <button
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg',
                      'hover:bg-warning-500/10 transition-colors'
                    )}
                    title="Pause"
                  >
                    <Pause className="h-4 w-4 text-warning-500" />
                  </button>
                ) : campaign.status === 'paused' ? (
                  <button
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg',
                      'hover:bg-success-500/10 transition-colors'
                    )}
                    title="Resume"
                  >
                    <Play className="h-4 w-4 text-success-500" />
                  </button>
                ) : null}
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

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {campaign.completedCalls.toLocaleString('en-US')} / {campaign.totalCalls.toLocaleString('en-US')} calls
                </span>
                <span className="font-medium">{campaign.progress}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-500',
                    statusConfig[campaign.status].barColor
                  )}
                  style={{ width: `${campaign.progress}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
