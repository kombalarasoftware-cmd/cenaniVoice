'use client';

import { Header } from '@/components/layout/header';
import { cn, formatDuration } from '@/lib/utils';
import React, { useState, useEffect, useCallback } from 'react';
import {
  PhoneCall,
  Search,
  Download,
  ChevronLeft,
  ChevronRight,
  Clock,
  Filter,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle,
  PhoneOff,
  PhoneMissed,
  Loader2,
  DollarSign,
  Cpu,
  Bot,
} from 'lucide-react';

import { API_V1 as API_BASE } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────
interface AgentCallLogItem {
  id: number;
  call_sid: string;
  to_number: string | null;
  from_number: string | null;
  customer_name: string | null;
  status: string;
  outcome: string | null;
  duration: number;
  started_at: string | null;
  ended_at: string | null;
  campaign_name: string | null;
  provider: string | null;
  matched_prefix: string | null;
  price_per_second: number | null;
  tariff_cost: number | null;
  tariff_description: string | null;
}

interface AgentCallLogResponse {
  items: AgentCallLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_duration_seconds: number;
  total_tariff_cost: number;
  avg_cost_per_call: number;
}

interface AgentOption {
  id: number;
  name: string;
}

interface Filters {
  search: string;
  date_from: string;
  date_to: string;
  status: string;
  outcome: string;
}

// ─── Helpers ─────────────────────────────────────────────────────
function getToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token') || '';
  }
  return '';
}

const headers = (): Record<string, string> => ({
  'Authorization': `Bearer ${getToken()}`,
  'Content-Type': 'application/json',
});

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const mins = String(d.getMinutes()).padStart(2, '0');
  return `${day}/${month}/${year} ${hours}:${mins}`;
}

function formatCost(cost: number | null): string {
  if (!cost || cost === 0) return '$0.0000';
  return `$${cost.toFixed(4)}`;
}

function formatCostColor(cost: number | null): string {
  if (!cost || cost === 0) return 'text-muted-foreground';
  if (cost < 0.01) return 'text-green-500';
  if (cost < 0.05) return 'text-yellow-500';
  return 'text-orange-500';
}

// ─── Status / Outcome Badges ─────────────────────────────────────
function StatusBadge({ status }: { status: string }): React.ReactElement {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/10 text-green-500',
    talking: 'bg-blue-500/10 text-blue-500',
    connected: 'bg-blue-500/10 text-blue-500',
    ringing: 'bg-yellow-500/10 text-yellow-500',
    queued: 'bg-gray-500/10 text-gray-500',
    failed: 'bg-red-500/10 text-red-500',
    no_answer: 'bg-orange-500/10 text-orange-500',
    busy: 'bg-purple-500/10 text-purple-500',
  };
  const icons: Record<string, React.ReactElement> = {
    completed: <CheckCircle className="h-3 w-3" />,
    failed: <AlertCircle className="h-3 w-3" />,
    no_answer: <PhoneMissed className="h-3 w-3" />,
    busy: <PhoneOff className="h-3 w-3" />,
  };
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', styles[status] || 'bg-gray-500/10 text-gray-500')}>
      {icons[status]}
      {status.replace(/_/g, ' ')}
    </span>
  );
}

// ─── Provider Badge ──────────────────────────────────────────────
const PROVIDER_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  openai:   { label: 'OpenAI',   color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  xai:      { label: 'xAI Grok', color: 'text-blue-500',    bg: 'bg-blue-500/10' },
  gemini:   { label: 'Gemini',   color: 'text-amber-500',   bg: 'bg-amber-500/10' },
  ultravox: { label: 'Ultravox', color: 'text-violet-500',  bg: 'bg-violet-500/10' },
};

function ProviderBadge({ provider }: { provider: string | null }): React.ReactElement {
  if (!provider) return <span className="text-xs text-muted-foreground">N/A</span>;
  const cfg = PROVIDER_CONFIG[provider] || { label: provider, color: 'text-gray-500', bg: 'bg-gray-500/10' };
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', cfg.bg, cfg.color)}>
      <Cpu className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}

// ─── Main Page ───────────────────────────────────────────────────
export default function AgentCallLogPage(): React.ReactElement {
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [calls, setCalls] = useState<AgentCallLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [showFilters, setShowFilters] = useState(false);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Summary
  const [totalDuration, setTotalDuration] = useState(0);
  const [totalTariffCost, setTotalTariffCost] = useState(0);
  const [avgCostPerCall, setAvgCostPerCall] = useState(0);

  const [filters, setFilters] = useState<Filters>({
    search: '',
    date_from: '',
    date_to: '',
    status: '',
    outcome: '',
  });

  // Load agents on mount
  useEffect(() => {
    const fetchAgents = async (): Promise<void> => {
      try {
        const resp = await fetch(`${API_BASE}/agents`, { headers: headers() });
        if (resp.ok) {
          const data = await resp.json();
          const list: AgentOption[] = data.map((a: { id: number; name: string }) => ({ id: a.id, name: a.name }));
          setAgents(list);
          if (list.length > 0) {
            setSelectedAgentId(String(list[0].id));
          }
        }
      } catch (e) {
        console.error('Failed to load agents:', e);
      } finally {
        setIsLoadingAgents(false);
      }
    };
    fetchAgents();
  }, []);

  // Fetch call log when agent or filters change
  const fetchCallLog = useCallback(async (): Promise<void> => {
    if (!selectedAgentId) return;
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('skip', String((page - 1) * pageSize));
      params.set('limit', String(pageSize));
      if (filters.search) params.set('search', filters.search);
      if (filters.date_from) params.set('date_from', new Date(filters.date_from).toISOString());
      if (filters.date_to) params.set('date_to', new Date(filters.date_to).toISOString());
      if (filters.status) params.set('status', filters.status);
      if (filters.outcome) params.set('outcome', filters.outcome);

      const resp = await fetch(
        `${API_BASE}/agents/${selectedAgentId}/call-log?${params.toString()}`,
        { headers: headers() }
      );
      if (resp.ok) {
        const data: AgentCallLogResponse = await resp.json();
        setCalls(data.items);
        setTotal(data.total);
        setTotalDuration(data.total_duration_seconds);
        setTotalTariffCost(data.total_tariff_cost);
        setAvgCostPerCall(data.avg_cost_per_call);
      }
    } catch (e) {
      console.error('Failed to load agent call log:', e);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAgentId, page, pageSize, filters]);

  useEffect(() => {
    fetchCallLog();
  }, [fetchCallLog]);

  // Reset page when agent changes
  useEffect(() => {
    setPage(1);
  }, [selectedAgentId]);

  const totalPages = Math.ceil(total / pageSize);

  const handleFilterChange = (key: keyof Filters, value: string): void => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = (): void => {
    setFilters({ search: '', date_from: '', date_to: '', status: '', outcome: '' });
    setPage(1);
  };

  const hasActiveFilters = Object.values(filters).some(v => v !== '');

  // CSV Export
  const handleExport = (): void => {
    if (calls.length === 0) return;
    const csvHeaders = ['Date', 'Customer', 'Number', 'Duration (s)', 'Status', 'Outcome', 'Provider', 'Prefix', 'Rate/min', 'Cost', 'Campaign'];
    const csvRows = calls.map(c => [
      c.started_at ? formatDate(c.started_at) : '',
      c.customer_name || '',
      c.to_number || '',
      String(c.duration),
      c.status,
      c.outcome || '',
      c.provider || '',
      c.matched_prefix || '',
      c.price_per_second != null ? c.price_per_second.toFixed(4) : '',
      c.tariff_cost != null ? c.tariff_cost.toFixed(4) : '',
      c.campaign_name || '',
    ]);
    const csv = [csvHeaders.join(','), ...csvRows.map(r => r.map(v => `"${v}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const agentName = agents.find(a => String(a.id) === selectedAgentId)?.name || 'agent';
    a.download = `agent-call-log-${agentName}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header title="Agent Call Log" />

      <div className="p-6 space-y-6">
        {/* Agent Selector + Actions */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          {/* Agent Select */}
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary-500" />
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="px-3 py-2 bg-background border border-border rounded-lg text-sm focus:ring-1 focus:ring-primary-500"
              disabled={isLoadingAgents}
            >
              {isLoadingAgents && <option>Loading...</option>}
              {agents.map(a => (
                <option key={a.id} value={String(a.id)}>{a.name}</option>
              ))}
            </select>
          </div>

          {/* Search */}
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search number or name..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-sm focus:ring-1 focus:ring-primary-500"
            />
          </div>

          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 border rounded-lg text-sm transition-colors',
              hasActiveFilters
                ? 'border-primary-500 text-primary-500'
                : 'border-border text-muted-foreground hover:text-foreground'
            )}
          >
            <Filter className="h-4 w-4" />
            Filters
            {hasActiveFilters && (
              <span className="bg-primary-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                {Object.values(filters).filter(v => v !== '').length}
              </span>
            )}
          </button>

          {/* Export */}
          <button
            onClick={handleExport}
            disabled={calls.length === 0}
            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>

        {/* Filter panel */}
        {showFilters && (
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">From Date</label>
                <input
                  type="date"
                  value={filters.date_from}
                  onChange={(e) => handleFilterChange('date_from', e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">To Date</label>
                <input
                  type="date"
                  value={filters.date_to}
                  onChange={(e) => handleFilterChange('date_to', e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
                >
                  <option value="">All</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="no_answer">No Answer</option>
                  <option value="busy">Busy</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Outcome</label>
                <select
                  value={filters.outcome}
                  onChange={(e) => handleFilterChange('outcome', e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-sm"
                >
                  <option value="">All</option>
                  <option value="success">Success</option>
                  <option value="voicemail">Voicemail</option>
                  <option value="no_answer">No Answer</option>
                  <option value="busy">Busy</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
            </div>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="mt-3 flex items-center gap-1 text-sm text-red-500 hover:text-red-600"
              >
                <X className="h-3 w-3" /> Clear Filters
              </button>
            )}
          </div>
        )}

        {/* Summary bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm text-muted-foreground">Page Calls</div>
            <div className="text-2xl font-bold mt-1">{calls.length} <span className="text-sm font-normal text-muted-foreground">/ {total}</span></div>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" /> Page Duration
            </div>
            <div className="text-2xl font-bold mt-1">{formatDuration(totalDuration)}</div>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <DollarSign className="h-3.5 w-3.5" /> Page Cost
            </div>
            <div className={cn('text-2xl font-bold mt-1', formatCostColor(totalTariffCost))}>
              {formatCost(totalTariffCost)}
            </div>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-sm text-muted-foreground">Avg Cost/Call</div>
            <div className={cn('text-2xl font-bold mt-1', formatCostColor(avgCostPerCall))}>
              {formatCost(avgCostPerCall)}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-muted/50 border-b border-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Date/Time</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Customer</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Number</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Duration</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Provider</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Prefix</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Rate/min</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">Cost</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={10} className="text-center py-12">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-primary-500" />
                      <p className="text-sm text-muted-foreground mt-2">Loading...</p>
                    </td>
                  </tr>
                ) : calls.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="text-center py-12">
                      <PhoneCall className="h-8 w-8 mx-auto text-muted-foreground/30" />
                      <p className="text-sm text-muted-foreground mt-2">
                        {selectedAgentId ? 'No calls found' : 'Select an agent'}
                      </p>
                    </td>
                  </tr>
                ) : (
                  calls.map((call) => (
                    <React.Fragment key={call.id}>
                      <tr
                        className={cn(
                          'border-b border-border hover:bg-muted/30 transition-colors cursor-pointer',
                          expandedRow === call.id && 'bg-muted/30'
                        )}
                        onClick={() => setExpandedRow(expandedRow === call.id ? null : call.id)}
                      >
                        <td className="px-4 py-3 text-sm">
                          {call.started_at ? formatDate(call.started_at) : '-'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          {call.customer_name || <span className="text-muted-foreground">—</span>}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs">
                          {call.to_number || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-muted-foreground" />
                            {formatDuration(call.duration)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={call.status} />
                        </td>
                        <td className="px-4 py-3">
                          <ProviderBadge provider={call.provider} />
                        </td>
                        <td className="px-4 py-3 text-sm font-mono">
                          {call.matched_prefix ? (
                            <span className="px-2 py-0.5 bg-blue-500/10 text-blue-500 rounded text-xs">{call.matched_prefix}</span>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-right font-mono">
                          {call.price_per_second != null ? `$${call.price_per_second.toFixed(4)}/min` : '—'}
                        </td>
                        <td className={cn('px-4 py-3 text-sm text-right font-bold', formatCostColor(call.tariff_cost))}>
                          {formatCost(call.tariff_cost)}
                        </td>
                        <td className="px-4 py-3">
                          {expandedRow === call.id
                            ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
                            : <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          }
                        </td>
                      </tr>
                      {/* Expanded Detail Row */}
                      {expandedRow === call.id && (
                        <tr className="bg-muted/20 border-b border-border">
                          <td colSpan={10} className="px-6 py-4">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">Call SID: </span>
                                <span className="font-mono text-xs">{call.call_sid}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">From: </span>
                                <span className="font-mono text-xs">{call.from_number || '-'}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Outcome: </span>
                                <span>{call.outcome?.replace(/_/g, ' ') || '-'}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Campaign: </span>
                                <span>{call.campaign_name || '-'}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Tariff: </span>
                                <span>{call.tariff_description || '-'}</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Duration: </span>
                                <span>{call.duration}s</span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Calculation: </span>
                                {call.price_per_second != null && call.duration > 0 ? (
                                  <span className="font-mono text-xs">
                                    {call.duration}s × (${call.price_per_second.toFixed(4)}/60) = {formatCost(call.tariff_cost)}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">No tariff match</span>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total}
              </span>
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                className="px-2 py-1 bg-background border border-border rounded text-sm"
              >
                <option value={20}>20/page</option>
                <option value={50}>50/page</option>
                <option value={100}>100/page</option>
              </select>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-2 border border-border rounded hover:bg-muted disabled:opacity-50"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="px-3 py-1 text-sm">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-2 border border-border rounded hover:bg-muted disabled:opacity-50"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
