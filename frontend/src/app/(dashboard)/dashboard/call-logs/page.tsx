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
} from 'lucide-react';

import { API_V1 as API_BASE } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────
interface CallLogResponse {
  id: number;
  call_sid: string;
  started_at: string;
  ended_at: string | null;
  duration: number;
  to_number: string;
  from_number: string;
  customer_name: string | null;
  agent_id: number | null;
  agent_name: string | null;
  campaign_id: number | null;
  campaign_name: string | null;
  status: string;
  outcome: string | null;
  sip_code: number | null;
  hangup_cause: string | null;
  summary: string | null;
  sentiment: string | null;
  tags: string[] | null;
  callback_requested: boolean;
  estimated_cost: number;
  provider: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cached_tokens: number | null;
  model_used: string | null;
  amd_status: string | null;
}

interface CallsResponse {
  items: CallLogResponse[];
  total: number;
  page: number;
  page_size: number;
}

interface FiltersResponse {
  campaigns: { id: number; name: string }[];
  agents: { id: number; name: string }[];
  statuses: string[];
  outcomes: string[];
}

interface Filters {
  search: string;
  date_from: string;
  date_to: string;
  campaign_id: string;
  agent_id: string;
  status: string;
  outcome: string;
}

// ─── Helpers ─────────────────────────────────────────────────────
function getToken() {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token') || '';
  }
  return '';
}

const headers = () => ({
  'Authorization': `Bearer ${getToken()}`,
  'Content-Type': 'application/json',
});

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const mins = String(d.getMinutes()).padStart(2, '0');
  return `${day}/${month}/${year} ${hours}:${mins}`;
}

function formatCost(cost: number) {
  if (!cost || cost === 0) return '$0.0000';
  return `$${cost.toFixed(4)}`;
}

function formatCostColor(cost: number) {
  if (!cost || cost === 0) return 'text-muted-foreground';
  if (cost < 0.01) return 'text-green-500';
  if (cost < 0.05) return 'text-yellow-500';
  return 'text-orange-500';
}

// ─── Provider Badge ──────────────────────────────────────────────
function ProviderBadge({ provider }: { provider: string | null }) {
  if (!provider) return <span className="text-xs text-muted-foreground">N/A</span>;

  const isUltravox = provider === 'ultravox';
  const isXai = provider === 'xai';
  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
      isXai
        ? 'bg-blue-500/10 text-blue-500'
        : isUltravox
          ? 'bg-violet-500/10 text-violet-500'
          : 'bg-emerald-500/10 text-emerald-500'
    )}>
      <Cpu className="h-3 w-3" />
      {isXai ? 'xAI Grok' : isUltravox ? 'Ultravox' : 'OpenAI'}
    </span>
  );
}

// ─── AMD Badge ───────────────────────────────────────────────────
function AmdBadge({ status }: { status: string | null }) {
  if (!status) return null;

  const isMachine = status === 'MACHINE';
  const isHuman = status === 'HUMAN';
  return (
    <span className={cn(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
      isMachine
        ? 'bg-red-500/10 text-red-500'
        : isHuman
          ? 'bg-green-500/10 text-green-500'
          : 'bg-yellow-500/10 text-yellow-500'
    )}>
      {isMachine ? '🤖 Machine' : isHuman ? '👤 Human' : '❓ Unsure'}
    </span>
  );
}

// ─── Status Badge ────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; bg: string }> = {
    completed: { color: 'text-green-500', bg: 'bg-green-500/10' },
    failed: { color: 'text-red-500', bg: 'bg-red-500/10' },
    no_answer: { color: 'text-orange-500', bg: 'bg-orange-500/10' },
    busy: { color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
    talking: { color: 'text-blue-500', bg: 'bg-blue-500/10' },
    connected: { color: 'text-blue-500', bg: 'bg-blue-500/10' },
    ringing: { color: 'text-purple-500', bg: 'bg-purple-500/10' },
    transferred: { color: 'text-amber-500', bg: 'bg-amber-500/10' },
    queued: { color: 'text-gray-500', bg: 'bg-gray-500/10' },
  };

  const cfg = config[status] || { color: 'text-gray-500', bg: 'bg-gray-500/10' };

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', cfg.bg, cfg.color)}>
      {status.replace('_', ' ')}
    </span>
  );
}

// ─── Outcome Badge ───────────────────────────────────────────────
function OutcomeBadge({ outcome }: { outcome: string | null }) {
  if (!outcome) return <span className="text-xs text-muted-foreground">N/A</span>;

  const config: Record<string, { color: string; bg: string }> = {
    success: { color: 'text-green-500', bg: 'bg-green-500/10' },
    voicemail: { color: 'text-purple-500', bg: 'bg-purple-500/10' },
    no_answer: { color: 'text-orange-500', bg: 'bg-orange-500/10' },
    busy: { color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
    failed: { color: 'text-red-500', bg: 'bg-red-500/10' },
    transferred: { color: 'text-blue-500', bg: 'bg-blue-500/10' },
    callback_scheduled: { color: 'text-cyan-500', bg: 'bg-cyan-500/10' },
  };

  const cfg = config[outcome] || { color: 'text-gray-500', bg: 'bg-gray-500/10' };

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', cfg.bg, cfg.color)}>
      {outcome.replace('_', ' ')}
    </span>
  );
}

// ─── SIP Code Badge ──────────────────────────────────────────────
const SIP_CODE_MAP: Record<number, { label: string; icon: string; color: string; bg: string }> = {
  200: { label: 'Answered', icon: '✅', color: 'text-green-500', bg: 'bg-green-500/10' },
  180: { label: 'Ringing', icon: '📞', color: 'text-blue-500', bg: 'bg-blue-500/10' },
  183: { label: 'Ringing', icon: '📞', color: 'text-blue-500', bg: 'bg-blue-500/10' },
  400: { label: 'Bad Request', icon: '⚠️', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  401: { label: 'Unauthorized', icon: '🔒', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  403: { label: 'Forbidden', icon: '🚫', color: 'text-red-500', bg: 'bg-red-500/10' },
  404: { label: 'Invalid Number', icon: '❌', color: 'text-red-500', bg: 'bg-red-500/10' },
  408: { label: 'No Answer', icon: '📵', color: 'text-orange-500', bg: 'bg-orange-500/10' },
  480: { label: 'Unavailable', icon: '📵', color: 'text-orange-500', bg: 'bg-orange-500/10' },
  484: { label: 'Invalid Number', icon: '❌', color: 'text-red-500', bg: 'bg-red-500/10' },
  486: { label: 'Busy', icon: '🔴', color: 'text-yellow-600', bg: 'bg-yellow-500/10' },
  487: { label: 'Cancelled', icon: '🚫', color: 'text-gray-500', bg: 'bg-gray-500/10' },
  488: { label: 'Not Acceptable', icon: '⚠️', color: 'text-amber-500', bg: 'bg-amber-500/10' },
  500: { label: 'Server Error', icon: '💥', color: 'text-red-500', bg: 'bg-red-500/10' },
  502: { label: 'Bad Gateway', icon: '💥', color: 'text-red-500', bg: 'bg-red-500/10' },
  503: { label: 'Service Down', icon: '🔧', color: 'text-red-500', bg: 'bg-red-500/10' },
  504: { label: 'Timeout', icon: '⏱️', color: 'text-orange-500', bg: 'bg-orange-500/10' },
  600: { label: 'Busy Everywhere', icon: '🔴', color: 'text-yellow-600', bg: 'bg-yellow-500/10' },
  603: { label: 'Declined', icon: '🚫', color: 'text-red-500', bg: 'bg-red-500/10' },
  604: { label: 'Not Found', icon: '❌', color: 'text-red-500', bg: 'bg-red-500/10' },
};

function SipCodeBadge({ code }: { code: number | null }) {
  if (!code) return <span className="text-xs text-muted-foreground">N/A</span>;

  const info = SIP_CODE_MAP[code];
  if (info) {
    return (
      <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', info.bg, info.color)}>
        {info.icon} {info.label}
      </span>
    );
  }

  // Fallback for unknown codes
  let color = 'text-gray-500';
  let bg = 'bg-gray-500/10';
  let label = `Code ${code}`;
  if (code >= 200 && code < 300) { color = 'text-green-500'; bg = 'bg-green-500/10'; label = 'Success'; }
  else if (code >= 400 && code < 500) { color = 'text-amber-500'; bg = 'bg-amber-500/10'; label = 'Client Error'; }
  else if (code >= 500) { color = 'text-red-500'; bg = 'bg-red-500/10'; label = 'Server Error'; }

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', bg, color)}>
      {label} ({code})
    </span>
  );
}

// ─── Call Result Badge (combines SIP + AMD + hangup into one label) ──
function CallResultBadge({ call }: { call: CallLogResponse }) {
  // AMD: Answering machine detected (MACHINE or NOTSURE)
  if (call.amd_status === 'MACHINE' || call.amd_status === 'NOTSURE' || call.outcome === 'voicemail') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-500">
        🤖 Voicemail
      </span>
    );
  }

  // SIP code based result
  if (call.sip_code) {
    const info = SIP_CODE_MAP[call.sip_code];
    if (info) {
      return (
        <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', info.bg, info.color)}>
          {info.icon} {info.label}
        </span>
      );
    }
  }

  // Hangup cause fallback
  if (call.hangup_cause) {
    const cause = call.hangup_cause.toLowerCase();
    if (cause.startsWith('amd:')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-500">
          🤖 Voicemail
        </span>
      );
    }
    if (cause.includes('normal')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-500">
          ✅ Answered
        </span>
      );
    }
    if (cause.includes('busy')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-600">
          🔴 Busy
        </span>
      );
    }
    if (cause.includes('no answer') || cause.includes('no_answer')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-500/10 text-orange-500">
          📵 No Answer
        </span>
      );
    }
    if (cause.includes('not found') || cause.includes('invalid')) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-500">
          ❌ Invalid Number
        </span>
      );
    }
  }

  // Status fallback
  if (call.status === 'completed' || call.status === 'talking') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-500">
        ✅ Answered
      </span>
    );
  }
  if (call.status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-500">
        ❌ Failed
      </span>
    );
  }
  if (call.status === 'no_answer') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-500/10 text-orange-500">
        📵 No Answer
      </span>
    );
  }
  if (call.status === 'busy') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-600">
        🔴 Busy
      </span>
    );
  }

  return <span className="text-xs text-muted-foreground">—</span>;
}

// ─── Main Page ───────────────────────────────────────────────────
export default function CallLogsPage() {
  const [loading, setLoading] = useState(true);
  const [calls, setCalls] = useState<CallLogResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Filters
  const [filters, setFilters] = useState<Filters>({
    search: '',
    date_from: '',
    date_to: '',
    campaign_id: '',
    agent_id: '',
    status: '',
    outcome: '',
  });

  // Filter options
  const [filterOptions, setFilterOptions] = useState<FiltersResponse | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch filter options
  const fetchFilterOptions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/calls/filters`, { headers: headers() });
      if (res.ok) {
        setFilterOptions(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch filter options:', err);
    }
  }, []);

  // Fetch calls
  const fetchCalls = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('skip', String((page - 1) * pageSize));
      params.append('limit', String(pageSize));

      if (filters.search) params.append('search', filters.search);
      if (filters.date_from) params.append('date_from', new Date(filters.date_from).toISOString());
      if (filters.date_to) params.append('date_to', new Date(filters.date_to).toISOString());
      if (filters.campaign_id) params.append('campaign_id', filters.campaign_id);
      if (filters.agent_id) params.append('agent_id', filters.agent_id);
      if (filters.status) params.append('status', filters.status);
      if (filters.outcome) params.append('outcome', filters.outcome);

      const res = await fetch(`${API_BASE}/calls?${params.toString()}`, { headers: headers() });

      if (res.ok) {
        const data: CallsResponse = await res.json();
        setCalls(data.items);
        setTotal(data.total);
      } else {
        setCalls([]);
        setTotal(0);
      }
    } catch (err) {
      console.error('Failed to fetch calls:', err);
      setCalls([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters]);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    fetchCalls();
  }, [fetchCalls]);

  // CSV Export
  const handleExport = () => {
    if (calls.length === 0) return;

    const headers = [
      'Date', 'Customer', 'Phone', 'Agent', 'Campaign', 'Duration',
      'Status', 'Outcome', 'Provider', 'Model', 'AMD', 'SIP Code', 'Hangup Cause',
      'Cost', 'Input Tokens', 'Output Tokens', 'Cached Tokens', 'Sentiment'
    ];

    const rows = calls.map(call => [
      formatDate(call.started_at),
      call.customer_name || '',
      call.to_number,
      call.agent_name || '',
      call.campaign_name || '',
      formatDuration(call.duration),
      call.status,
      call.outcome || '',
      call.provider || '',
      call.model_used || '',
      call.amd_status || '',
      call.sip_code || '',
      call.hangup_cause || '',
      (call.estimated_cost || 0).toFixed(4),
      call.input_tokens || '',
      call.output_tokens || '',
      call.cached_tokens || '',
      call.sentiment || '',
    ]);

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `call-logs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({
      search: '',
      date_from: '',
      date_to: '',
      campaign_id: '',
      agent_id: '',
      status: '',
      outcome: '',
    });
    setPage(1);
  };

  // Pagination
  const totalPages = Math.ceil(total / pageSize);
  const startIndex = (page - 1) * pageSize + 1;
  const endIndex = Math.min(page * pageSize, total);

  return (
    <div className="min-h-screen">
      <Header
        title="Call Logs"
        description="View and analyze call detail records"
      />

      <div className="p-6 space-y-6">
        {/* Header Actions */}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Call Logs</h2>
          <button
            onClick={handleExport}
            disabled={calls.length === 0}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
              calls.length === 0
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-primary-500 hover:bg-primary-600 text-white'
            )}
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>

        {/* Cost Summary Bar */}
        {calls.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <PhoneCall className="h-4 w-4" />
                Total Calls
              </div>
              <p className="text-2xl font-bold">{total}</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                Page Total Cost
              </div>
              <p className={cn('text-2xl font-bold font-mono', formatCostColor(
                calls.reduce((sum, c) => sum + (c.estimated_cost || 0), 0)
              ))}>
                {formatCost(calls.reduce((sum, c) => sum + (c.estimated_cost || 0), 0))}
              </p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Clock className="h-4 w-4" />
                Avg Duration
              </div>
              <p className="text-2xl font-bold">
                {calls.length > 0
                  ? `${Math.round(calls.reduce((sum, c) => sum + (c.duration || 0), 0) / calls.length)}s`
                  : '-'}
              </p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                Avg Cost / Call
              </div>
              <p className={cn('text-2xl font-bold font-mono', formatCostColor(
                calls.reduce((sum, c) => sum + (c.estimated_cost || 0), 0) / calls.length
              ))}>
                {formatCost(calls.reduce((sum, c) => sum + (c.estimated_cost || 0), 0) / calls.length)}
              </p>
            </div>
          </div>
        )}

        {/* Filters Bar */}
        <div className="space-y-4">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Search */}
            <div className="relative flex-1 min-w-[250px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search customer, phone, call SID..."
                value={filters.search}
                onChange={(e) => {
                  setFilters({ ...filters, search: e.target.value });
                  setPage(1);
                }}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
              />
            </div>

            {/* Show/Hide Filters */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors',
                showFilters
                  ? 'bg-primary-500 text-white border-primary-500'
                  : 'bg-background border-border hover:bg-muted'
              )}
            >
              <Filter className="h-4 w-4" />
              Filters
              {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {/* Clear Filters */}
            <button
              onClick={clearFilters}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
            >
              <X className="h-4 w-4" />
              Clear
            </button>
          </div>

          {/* Expanded Filters */}
          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-xl bg-card border border-border">
              {/* Date From */}
              <div>
                <label className="block text-sm font-medium mb-2">Date From</label>
                <input
                  type="date"
                  value={filters.date_from}
                  onChange={(e) => {
                    setFilters({ ...filters, date_from: e.target.value });
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>

              {/* Date To */}
              <div>
                <label className="block text-sm font-medium mb-2">Date To</label>
                <input
                  type="date"
                  value={filters.date_to}
                  onChange={(e) => {
                    setFilters({ ...filters, date_to: e.target.value });
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
                />
              </div>

              {/* Campaign */}
              <div>
                <label className="block text-sm font-medium mb-2">Campaign</label>
                <select
                  value={filters.campaign_id}
                  onChange={(e) => {
                    setFilters({ ...filters, campaign_id: e.target.value });
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
                >
                  <option value="">All Campaigns</option>
                  {filterOptions?.campaigns.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              {/* Agent */}
              <div>
                <label className="block text-sm font-medium mb-2">Agent</label>
                <select
                  value={filters.agent_id}
                  onChange={(e) => {
                    setFilters({ ...filters, agent_id: e.target.value });
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
                >
                  <option value="">All Agents</option>
                  {filterOptions?.agents.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div>
                <label className="block text-sm font-medium mb-2">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => {
                    setFilters({ ...filters, status: e.target.value });
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
                >
                  <option value="">All Status</option>
                  <option value="queued">Queued</option>
                  <option value="ringing">Ringing</option>
                  <option value="connected">Connected</option>
                  <option value="talking">Talking</option>
                  <option value="on_hold">On Hold</option>
                  <option value="transferred">Transferred</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="no_answer">No Answer</option>
                  <option value="busy">Busy</option>
                </select>
              </div>

              {/* Outcome */}
              <div>
                <label className="block text-sm font-medium mb-2">Outcome</label>
                <select
                  value={filters.outcome}
                  onChange={(e) => {
                    setFilters({ ...filters, outcome: e.target.value });
                    setPage(1);
                  }}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none transition-colors"
                >
                  <option value="">All Outcomes</option>
                  <option value="success">Success</option>
                  <option value="voicemail">Voicemail</option>
                  <option value="no_answer">No Answer</option>
                  <option value="busy">Busy</option>
                  <option value="failed">Failed</option>
                  <option value="transferred">Transferred</option>
                  <option value="callback_scheduled">Callback Scheduled</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : calls.length === 0 ? (
          // Empty State
          <div className="flex flex-col items-center justify-center py-20 rounded-xl border border-border bg-card">
            <PhoneCall className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No call records found</h3>
            <p className="text-sm text-muted-foreground">
              Try adjusting your filters or search criteria
            </p>
          </div>
        ) : (
          <>
            {/* Data Table */}
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="text-left py-3 px-4 font-medium">Date/Time</th>
                      <th className="text-left py-3 px-4 font-medium">Customer</th>
                      <th className="text-left py-3 px-4 font-medium">Agent</th>
                      <th className="text-left py-3 px-4 font-medium">Campaign</th>
                      <th className="text-left py-3 px-4 font-medium">Duration</th>
                      <th className="text-left py-3 px-4 font-medium">Result</th>
                      <th className="text-left py-3 px-4 font-medium">Status</th>
                      <th className="text-left py-3 px-4 font-medium">Provider</th>
                      <th className="text-right py-3 px-4 font-medium">Cost</th>
                      <th className="text-center py-3 px-4 font-medium w-8"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {calls.map((call) => (
                      <React.Fragment key={call.id}>
                        <tr
                          onClick={() => setExpandedRow(expandedRow === call.id ? null : call.id)}
                          className={cn(
                            'border-b border-border cursor-pointer transition-colors',
                            expandedRow === call.id ? 'bg-primary-500/5' : 'hover:bg-muted/50'
                          )}
                        >
                          <td className="py-3 px-4 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <Clock className="h-4 w-4 text-muted-foreground" />
                              {formatDate(call.started_at)}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div>
                              {call.customer_name ? (
                                <>
                                  <p className="font-medium">{call.customer_name}</p>
                                  <p className="text-xs text-muted-foreground">{call.to_number}</p>
                                </>
                              ) : (
                                <p className="font-medium">{call.to_number}</p>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            {call.agent_name || <span className="text-muted-foreground">N/A</span>}
                          </td>
                          <td className="py-3 px-4">
                            {call.campaign_name || <span className="text-muted-foreground">N/A</span>}
                          </td>
                          <td className="py-3 px-4 font-mono">
                            {formatDuration(call.duration)}
                          </td>
                          <td className="py-3 px-4">
                            <CallResultBadge call={call} />
                          </td>
                          <td className="py-3 px-4">
                            <StatusBadge status={call.status} />
                          </td>
                          <td className="py-3 px-4">
                            <ProviderBadge provider={call.provider} />
                          </td>
                          <td className={cn('py-3 px-4 text-right font-mono', formatCostColor(call.estimated_cost))}>
                            {formatCost(call.estimated_cost)}
                          </td>
                          <td className="py-3 px-4 text-center">
                            {expandedRow === call.id ? (
                              <ChevronUp className="h-4 w-4 text-muted-foreground mx-auto" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-muted-foreground mx-auto" />
                            )}
                          </td>
                        </tr>

                        {/* Expanded Detail Row */}
                        {expandedRow === call.id && (
                          <tr className="bg-muted/20">
                            <td colSpan={10} className="py-4 px-4">
                              <div className="space-y-4">
                                {/* Summary */}
                                {call.summary && (
                                  <div>
                                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                                      <CheckCircle className="h-4 w-4 text-primary-500" />
                                      Summary
                                    </h4>
                                    <p className="text-sm text-muted-foreground pl-6">
                                      {call.summary}
                                    </p>
                                  </div>
                                )}

                                {/* Details Grid */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pl-6">
                                  {/* Cost Detail */}
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-1">Cost</p>
                                    <p className={cn('text-sm font-medium font-mono', formatCostColor(call.estimated_cost))}>
                                      {formatCost(call.estimated_cost)}
                                    </p>
                                  </div>

                                  {/* SIP Code */}
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-1">SIP Code</p>
                                    <SipCodeBadge code={call.sip_code} />
                                  </div>

                                  {/* Hangup Cause */}
                                  <div>
                                    <p className="text-xs text-muted-foreground mb-1">Hangup Cause</p>
                                    <p className="text-sm font-medium">
                                      {call.hangup_cause || 'N/A'}
                                    </p>
                                  </div>

                                  {/* AMD Status */}
                                  {call.amd_status && (
                                    <div>
                                      <p className="text-xs text-muted-foreground mb-1">AMD</p>
                                      <AmdBadge status={call.amd_status} />
                                    </div>
                                  )}

                                  {/* Sentiment */}
                                  {call.sentiment && (
                                    <div>
                                      <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                                      <p className={cn(
                                        'text-sm font-medium',
                                        call.sentiment === 'positive' ? 'text-green-500' :
                                        call.sentiment === 'negative' ? 'text-red-500' :
                                        'text-muted-foreground'
                                      )}>
                                        {call.sentiment}
                                      </p>
                                    </div>
                                  )}

                                  {/* Model */}
                                  {call.model_used && (
                                    <div>
                                      <p className="text-xs text-muted-foreground mb-1">Model</p>
                                      <p className="text-sm font-medium font-mono">{call.model_used}</p>
                                    </div>
                                  )}

                                  {/* Callback */}
                                  {call.callback_requested && (
                                    <div>
                                      <p className="text-xs text-muted-foreground mb-1">Callback</p>
                                      <span className="inline-flex items-center gap-1 text-sm font-medium text-amber-500">
                                        <AlertCircle className="h-3 w-3" />
                                        Requested
                                      </span>
                                    </div>
                                  )}
                                </div>

                                {/* Cost & Usage Detail */}
                                <div className="pl-6">
                                  <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                                    <DollarSign className="h-4 w-4" />
                                    Cost Breakdown
                                  </h4>

                                  {call.provider === 'ultravox' ? (
                                    // Ultravox: minute-based billing
                                    <div className="flex items-center gap-6 text-xs">
                                      <div>
                                        <span className="text-muted-foreground">Provider: </span>
                                        <span className="font-medium text-violet-500">Ultravox</span>
                                      </div>
                                      <div>
                                        <span className="text-muted-foreground">Duration: </span>
                                        <span className="font-medium">{call.duration ? `${call.duration}s` : '-'}</span>
                                      </div>
                                      <div>
                                        <span className="text-muted-foreground">Billed Units: </span>
                                        <span className="font-medium">{call.duration ? `${Math.ceil(call.duration / 6)} deciminutes` : '-'}</span>
                                      </div>
                                      <div>
                                        <span className="text-muted-foreground">Rate: </span>
                                        <span className="font-medium">$0.005/6s</span>
                                      </div>
                                      <div>
                                        <span className="text-muted-foreground">Total: </span>
                                        <span className={cn('font-medium font-mono', formatCostColor(call.estimated_cost))}>
                                          {formatCost(call.estimated_cost)}
                                        </span>
                                      </div>
                                    </div>
                                  ) : (
                                    // OpenAI: token-based billing
                                    <div className="flex items-center gap-6 text-xs">
                                      <div>
                                        <span className="text-muted-foreground">Provider: </span>
                                        <span className="font-medium text-emerald-500">OpenAI</span>
                                      </div>
                                      {call.model_used && (
                                        <div>
                                          <span className="text-muted-foreground">Model: </span>
                                          <span className="font-medium">{call.model_used}</span>
                                        </div>
                                      )}
                                      {call.input_tokens != null && call.input_tokens > 0 && (
                                        <div>
                                          <span className="text-muted-foreground">Input: </span>
                                          <span className="font-medium">{call.input_tokens.toLocaleString()} tokens</span>
                                        </div>
                                      )}
                                      {call.output_tokens != null && call.output_tokens > 0 && (
                                        <div>
                                          <span className="text-muted-foreground">Output: </span>
                                          <span className="font-medium">{call.output_tokens.toLocaleString()} tokens</span>
                                        </div>
                                      )}
                                      {call.cached_tokens != null && call.cached_tokens > 0 && (
                                        <div>
                                          <span className="text-muted-foreground">Cached: </span>
                                          <span className="font-medium">{call.cached_tokens.toLocaleString()} tokens</span>
                                        </div>
                                      )}
                                      <div>
                                        <span className="text-muted-foreground">Total: </span>
                                        <span className={cn('font-medium font-mono', formatCostColor(call.estimated_cost))}>
                                          {formatCost(call.estimated_cost)}
                                        </span>
                                      </div>
                                    </div>
                                  )}
                                </div>

                                {/* Tags */}
                                {call.tags && call.tags.length > 0 && (
                                  <div className="pl-6">
                                    <h4 className="text-sm font-semibold mb-2">Tags</h4>
                                    <div className="flex flex-wrap gap-2">
                                      {call.tags.map((tag, idx) => (
                                        <span
                                          key={idx}
                                          className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-500/10 text-primary-500"
                                        >
                                          {tag}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Call IDs */}
                                <div className="pl-6 pt-2 border-t border-border">
                                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                    <span>Call ID: <span className="font-mono">{call.id}</span></span>
                                    <span>SID: <span className="font-mono">{call.call_sid}</span></span>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex}-{endIndex} of {total} calls
              </div>

              <div className="flex items-center gap-4">
                {/* Items per page */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Per page:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    className="px-2 py-1 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
                  >
                    <option value="20">20</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                  </select>
                </div>

                {/* Page navigation */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className={cn(
                      'flex items-center gap-1 px-3 py-1.5 rounded-lg transition-colors',
                      page === 1
                        ? 'bg-muted text-muted-foreground cursor-not-allowed'
                        : 'bg-background border border-border hover:bg-muted'
                    )}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Prev
                  </button>

                  {/* Page numbers */}
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (page <= 3) {
                        pageNum = i + 1;
                      } else if (page >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = page - 2 + i;
                      }

                      return (
                        <button
                          key={i}
                          onClick={() => setPage(pageNum)}
                          className={cn(
                            'w-9 h-9 rounded-lg transition-colors',
                            page === pageNum
                              ? 'bg-primary-500 text-white'
                              : 'bg-background border border-border hover:bg-muted'
                          )}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className={cn(
                      'flex items-center gap-1 px-3 py-1.5 rounded-lg transition-colors',
                      page === totalPages
                        ? 'bg-muted text-muted-foreground cursor-not-allowed'
                        : 'bg-background border border-border hover:bg-muted'
                    )}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
