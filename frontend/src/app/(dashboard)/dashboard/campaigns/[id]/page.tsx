'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  Megaphone,
  Play,
  Pause,
  Square,
  Save,
  Loader2,
  Phone,
  Users,
  CheckCircle,
  Clock,
  Calendar,
  TrendingUp,
  AlertCircle,
} from 'lucide-react';

interface CampaignDetail {
  id: number;
  name: string;
  description: string;
  agent_id?: number;
  agent_name?: string;
  status: string;
  total_numbers: number;
  completed_calls: number;
  successful_calls: number;
  failed_calls: number;
  active_calls: number;
  scheduled_date?: string;
  max_concurrent_calls: number;
  retry_attempts: number;
  retry_delay_minutes: number;
  created_at: string;
  updated_at: string;
}

interface Agent {
  id: number;
  name: string;
}

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;

  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  // Editable fields
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [agentId, setAgentId] = useState<number | undefined>();
  const [maxConcurrent, setMaxConcurrent] = useState(5);
  const [retryAttempts, setRetryAttempts] = useState(2);
  const [retryDelay, setRetryDelay] = useState(30);

  const fetchCampaign = useCallback(async () => {
    try {
      setError('');
      const data = await api.get<CampaignDetail>(`/campaigns/${campaignId}`);
      setCampaign(data);
      setName(data.name);
      setDescription(data.description || '');
      setAgentId(data.agent_id);
      setMaxConcurrent(data.max_concurrent_calls || 5);
      setRetryAttempts(data.retry_attempts || 2);
      setRetryDelay(data.retry_delay_minutes || 30);
    } catch (err) {
      console.error('Failed to fetch campaign:', err);
      setError(err instanceof Error ? err.message : 'Failed to load campaign');
    } finally {
      setIsLoading(false);
    }
  }, [campaignId]);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await api.get<Agent[]>('/agents');
      setAgents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    }
  }, []);

  useEffect(() => {
    fetchCampaign();
    fetchAgents();
  }, [fetchCampaign, fetchAgents]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.put(`/campaigns/${campaignId}`, {
        name,
        description,
        agent_id: agentId,
        max_concurrent_calls: maxConcurrent,
        retry_attempts: retryAttempts,
        retry_delay_minutes: retryDelay,
      });
      toast.success('Campaign updated');
      fetchCampaign();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save campaign');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAction = async (action: 'pause' | 'resume' | 'stop') => {
    try {
      await api.post(`/campaigns/${campaignId}/${action}`);
      toast.success(`Campaign ${action === 'pause' ? 'paused' : action === 'resume' ? 'resumed' : 'stopped'}`);
      fetchCampaign();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : `Failed to ${action} campaign`);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="p-6">
        <Link href="/dashboard/campaigns" className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </Link>
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-error-500 mx-auto mb-4" />
          <p className="text-error-500 mb-4">{error || 'Campaign not found'}</p>
          <button
            onClick={fetchCampaign}
            className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const progress = campaign.total_numbers > 0
    ? Math.round((campaign.completed_calls / campaign.total_numbers) * 100)
    : 0;
  const successRate = campaign.completed_calls > 0
    ? Math.round((campaign.successful_calls / campaign.completed_calls) * 100)
    : 0;

  const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
    draft: { label: 'Draft', color: 'text-muted-foreground', bg: 'bg-muted' },
    scheduled: { label: 'Scheduled', color: 'text-warning-500', bg: 'bg-warning-500/10' },
    running: { label: 'Running', color: 'text-success-500', bg: 'bg-success-500/10' },
    paused: { label: 'Paused', color: 'text-warning-500', bg: 'bg-warning-500/10' },
    completed: { label: 'Completed', color: 'text-primary-500', bg: 'bg-primary-500/10' },
  };

  const status = statusConfig[campaign.status] || statusConfig.draft;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard/campaigns" className="p-2 rounded-lg hover:bg-muted transition-colors">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500/20 to-secondary-500/20">
                <Megaphone className="h-5 w-5 text-primary-500" />
              </div>
              <div>
                <h1 className="text-lg font-semibold">{campaign.name}</h1>
                <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', status.bg, status.color)}>
                  {status.label}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {campaign.status === 'running' && (
              <>
                <button
                  onClick={() => handleAction('pause')}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-warning-500/10 hover:bg-warning-500/20 text-warning-500 text-sm font-medium transition-colors"
                >
                  <Pause className="h-4 w-4" />
                  Pause
                </button>
                <button
                  onClick={() => handleAction('stop')}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-error-500/10 hover:bg-error-500/20 text-error-500 text-sm font-medium transition-colors"
                >
                  <Square className="h-4 w-4" />
                  Stop
                </button>
              </>
            )}
            {(campaign.status === 'paused' || campaign.status === 'scheduled' || campaign.status === 'draft') && (
              <button
                onClick={() => handleAction('resume')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-success-500/10 hover:bg-success-500/20 text-success-500 text-sm font-medium transition-colors"
              >
                <Play className="h-4 w-4" />
                {campaign.status === 'draft' ? 'Start' : 'Resume'}
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium transition-colors disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Total Numbers</span>
            </div>
            <p className="text-2xl font-bold">{campaign.total_numbers.toLocaleString('en-US')}</p>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Active Calls</span>
            </div>
            <p className="text-2xl font-bold text-success-500">{campaign.active_calls}</p>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Completed</span>
            </div>
            <p className="text-2xl font-bold">{campaign.completed_calls.toLocaleString('en-US')}</p>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Success Rate</span>
            </div>
            <p className="text-2xl font-bold text-primary-500">{successRate}%</p>
          </div>
          <div className="p-4 rounded-xl bg-card border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Progress</span>
            </div>
            <p className="text-2xl font-bold">{progress}%</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground">Campaign Progress</span>
            <span className="font-medium">{campaign.completed_calls} / {campaign.total_numbers} calls</span>
          </div>
          <div className="h-3 bg-muted rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                campaign.status === 'running' ? 'bg-success-500' : 'bg-primary-500'
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Edit Form */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4 p-6 rounded-xl bg-card border border-border">
            <h2 className="text-lg font-semibold">Campaign Details</h2>

            <div className="space-y-2">
              <label className="text-sm font-medium">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-2.5 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-4 py-2.5 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Agent</label>
              <select
                value={agentId || ''}
                onChange={(e) => setAgentId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-4 py-2.5 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select agent...</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-4 p-6 rounded-xl bg-card border border-border">
            <h2 className="text-lg font-semibold">Call Settings</h2>

            <div className="space-y-2">
              <label className="text-sm font-medium">Max Concurrent Calls</label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxConcurrent}
                onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                className="w-full px-4 py-2.5 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Retry Attempts</label>
              <input
                type="number"
                min={0}
                max={10}
                value={retryAttempts}
                onChange={(e) => setRetryAttempts(Number(e.target.value))}
                className="w-full px-4 py-2.5 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Retry Delay (minutes)</label>
              <input
                type="number"
                min={1}
                max={1440}
                value={retryDelay}
                onChange={(e) => setRetryDelay(Number(e.target.value))}
                className="w-full px-4 py-2.5 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="pt-2 text-xs text-muted-foreground space-y-1">
              <div className="flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" />
                Created: {new Date(campaign.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                Updated: {new Date(campaign.updated_at).toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
