'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import Link from 'next/link';
import {
  Megaphone,
  Play,
  Pause,
  MoreVertical,
  Plus,
  Calendar,
  Users,
  Phone,
  CheckCircle,
  Clock,
  TrendingUp,
  Filter,
  Search,
} from 'lucide-react';

interface Campaign {
  id: string;
  name: string;
  description: string;
  agentName: string;
  status: 'draft' | 'scheduled' | 'running' | 'paused' | 'completed';
  totalNumbers: number;
  completedCalls: number;
  successfulCalls: number;
  activeCalls: number;
  scheduledDate?: string;
  createdAt: string;
}

const mockCampaigns: Campaign[] = [];

export default function CampaignsPage() {
  const [filter, setFilter] = useState<'all' | Campaign['status']>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCampaigns = mockCampaigns.filter((campaign) => {
    if (filter !== 'all' && campaign.status !== filter) return false;
    if (searchQuery && !campaign.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const statusConfig = {
    draft: { label: 'Draft', color: 'text-muted-foreground', bg: 'bg-muted' },
    scheduled: { label: 'Scheduled', color: 'text-warning-500', bg: 'bg-warning-500/10' },
    running: { label: 'Running', color: 'text-success-500', bg: 'bg-success-500/10' },
    paused: { label: 'Paused', color: 'text-warning-500', bg: 'bg-warning-500/10' },
    completed: { label: 'Completed', color: 'text-primary-500', bg: 'bg-primary-500/10' },
  };

  return (
    <div className="min-h-screen">
      <Header
        title="Campaigns"
        description="Manage your outbound calling campaigns"
        action={{
          label: 'Create Campaign',
          onClick: () => {},
        }}
      />

      <div className="p-6">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2">
            {(['all', 'running', 'paused', 'scheduled', 'completed', 'draft'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setFilter(status)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  filter === status
                    ? 'bg-primary-500 text-white'
                    : 'bg-muted text-muted-foreground hover:text-foreground'
                )}
              >
                {status === 'all' ? 'All' : statusConfig[status].label}
              </button>
            ))}
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search campaigns..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                'pl-9 pr-4 py-2 rounded-lg bg-background border border-border',
                'focus:border-primary-500 focus:outline-none transition-colors',
                'w-64'
              )}
            />
          </div>
        </div>

        {/* Stats overview */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success-500/10">
                <Play className="h-5 w-5 text-success-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockCampaigns.filter((c) => c.status === 'running').length}
                </p>
                <p className="text-sm text-muted-foreground">Active Campaigns</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-500/10">
                <Phone className="h-5 w-5 text-primary-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockCampaigns.reduce((acc, c) => acc + c.activeCalls, 0)}
                </p>
                <p className="text-sm text-muted-foreground">Active Calls</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary-500/10">
                <Users className="h-5 w-5 text-secondary-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockCampaigns.reduce((acc, c) => acc + c.totalNumbers, 0).toLocaleString('en-US')}
                </p>
                <p className="text-sm text-muted-foreground">Total Numbers</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-500/10">
                <TrendingUp className="h-5 w-5 text-accent-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockCampaigns.reduce((acc, c) => acc + c.completedCalls, 0) > 0
                    ? Math.round(
                        (mockCampaigns.reduce((acc, c) => acc + c.successfulCalls, 0) /
                          mockCampaigns.reduce((acc, c) => acc + c.completedCalls, 0)) *
                          100
                      )
                    : 0}%
                </p>
                <p className="text-sm text-muted-foreground">Avg Success Rate</p>
              </div>
            </div>
          </div>
        </div>

        {/* Campaigns list */}
        <div className="space-y-4">
          {filteredCampaigns.map((campaign) => {
            const progress = Math.round((campaign.completedCalls / campaign.totalNumbers) * 100);
            const successRate = campaign.completedCalls > 0
              ? Math.round((campaign.successfulCalls / campaign.completedCalls) * 100)
              : 0;

            return (
              <div
                key={campaign.id}
                className={cn(
                  'p-6 rounded-xl border border-border bg-card',
                  'hover:shadow-lg transition-all duration-300 group'
                )}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Left section */}
                  <div className="flex-1">
                    <div className="flex items-start gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500/20 to-secondary-500/20">
                        <Megaphone className="h-6 w-6 text-primary-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <Link
                            href={`/dashboard/campaigns/${campaign.id}`}
                            className="font-semibold hover:text-primary-500 transition-colors"
                          >
                            {campaign.name}
                          </Link>
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
                            <span className="flex items-center gap-1 text-xs text-success-500">
                              <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success-400 opacity-75" />
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-success-500" />
                              </span>
                              {campaign.activeCalls} active
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">
                          {campaign.description}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Users className="h-3.5 w-3.5" />
                            Agent: {campaign.agentName}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            Created: {campaign.createdAt}
                          </span>
                          {campaign.scheduledDate && (
                            <span className="flex items-center gap-1">
                              <Clock className="h-3.5 w-3.5" />
                              Scheduled: {campaign.scheduledDate}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Progress section */}
                  <div className="lg:w-64">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium">{progress}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden mb-2">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          campaign.status === 'running' ? 'bg-success-500' : 'bg-primary-500'
                        )}
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{campaign.completedCalls.toLocaleString('en-US')} / {campaign.totalNumbers.toLocaleString('en-US')} calls</span>
                      <span>{successRate}% success</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 lg:pl-4 lg:border-l lg:border-border">
                    {campaign.status === 'running' ? (
                      <button
                        className={cn(
                          'flex h-9 w-9 items-center justify-center rounded-lg',
                          'bg-warning-500/10 hover:bg-warning-500/20 text-warning-500',
                          'transition-colors'
                        )}
                        title="Pause"
                      >
                        <Pause className="h-4 w-4" />
                      </button>
                    ) : campaign.status === 'paused' || campaign.status === 'scheduled' ? (
                      <button
                        className={cn(
                          'flex h-9 w-9 items-center justify-center rounded-lg',
                          'bg-success-500/10 hover:bg-success-500/20 text-success-500',
                          'transition-colors'
                        )}
                        title="Start"
                      >
                        <Play className="h-4 w-4" />
                      </button>
                    ) : null}
                    <button
                      className={cn(
                        'flex h-9 w-9 items-center justify-center rounded-lg',
                        'hover:bg-muted transition-colors'
                      )}
                    >
                      <MoreVertical className="h-4 w-4 text-muted-foreground" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {filteredCampaigns.length === 0 && (
          <div className="text-center py-12">
            <Megaphone className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No campaigns found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery
                ? 'Try a different search term'
                : 'Create your first campaign to get started'}
            </p>
            <button
              className={cn(
                'inline-flex items-center gap-2 px-4 py-2 rounded-lg',
                'bg-primary-500 hover:bg-primary-600 text-white',
                'font-medium transition-colors'
              )}
            >
              <Plus className="h-4 w-4" />
              Create Campaign
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
