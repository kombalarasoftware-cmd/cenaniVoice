'use client';

import { cn, formatDuration } from '@/lib/utils';
import {
  Clock,
  Zap,
  MessageSquare,
  AlertTriangle,
  TrendingUp,
  Download,
  FileText,
  FileJson,
  DollarSign,
} from 'lucide-react';

export interface CallMetrics {
  duration: number; // seconds
  latency: number; // ms - average response latency
  interrupts: number; // number of interruptions
  turnCount: number; // conversation turns
  tokensUsed?: number;
  audioSeconds?: number;
}

export interface CostBreakdown {
  // OpenAI token-based fields (optional for Ultravox)
  input_tokens?: { text: number; audio: number; total: number };
  output_tokens?: { text: number; audio: number; total: number };
  cost: {
    input_text?: number;
    input_audio?: number;
    output_text?: number;
    output_audio?: number;
    total: number;
  };
  model?: string;
  // Ultravox minute-based fields
  provider?: string;
  duration_seconds?: number;
  rate_per_minute?: number;
}

interface CallMetricsBarProps {
  metrics: CallMetrics;
  cost?: CostBreakdown | null;
  isActive?: boolean;
  onExportTranscript?: (format: 'txt' | 'json' | 'pdf') => void;
  className?: string;
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(amount: number): string {
  if (amount < 0.01) return `$${amount.toFixed(4)}`;
  return `$${amount.toFixed(2)}`;
}

function MetricCard({ 
  icon: Icon, 
  label, 
  value, 
  subValue,
  colorClass = 'text-primary-500',
  bgClass = 'bg-primary-500/10',
}: { 
  icon: typeof Clock;
  label: string;
  value: string | number;
  subValue?: string;
  colorClass?: string;
  bgClass?: string;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-2">
      <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg', bgClass)}>
        <Icon className={cn('h-4 w-4', colorClass)} />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-semibold text-sm">
          {value}
          {subValue && (
            <span className="text-xs text-muted-foreground ml-1">{subValue}</span>
          )}
        </p>
      </div>
    </div>
  );
}

export function CallMetricsBar({ 
  metrics, 
  cost,
  isActive = false, 
  onExportTranscript,
  className 
}: CallMetricsBarProps) {
  const latencyStatus = metrics.latency < 500 
    ? { color: 'text-green-500', bg: 'bg-green-500/10', label: 'Good' }
    : metrics.latency < 1000 
      ? { color: 'text-yellow-500', bg: 'bg-yellow-500/10', label: 'Fair' }
      : { color: 'text-red-500', bg: 'bg-red-500/10', label: 'Slow' };

  return (
    <div className={cn(
      'flex items-center justify-between rounded-xl border border-border bg-card',
      className
    )}>
      {/* Metrics */}
      <div className="flex items-center divide-x divide-border">
        <MetricCard 
          icon={Clock}
          label="Duration"
          value={formatDuration(metrics.duration)}
          colorClass="text-blue-500"
          bgClass="bg-blue-500/10"
        />
        
        <MetricCard 
          icon={Zap}
          label="Latency"
          value={formatLatency(metrics.latency)}
          subValue={latencyStatus.label}
          colorClass={latencyStatus.color}
          bgClass={latencyStatus.bg}
        />
        
        <MetricCard 
          icon={MessageSquare}
          label="Turns"
          value={metrics.turnCount}
          colorClass="text-purple-500"
          bgClass="bg-purple-500/10"
        />
        
        <MetricCard 
          icon={AlertTriangle}
          label="Interrupts"
          value={metrics.interrupts}
          colorClass={metrics.interrupts > 5 ? 'text-orange-500' : 'text-gray-500'}
          bgClass={metrics.interrupts > 5 ? 'bg-orange-500/10' : 'bg-gray-500/10'}
        />
        
        {metrics.tokensUsed && (
          <MetricCard 
            icon={TrendingUp}
            label="Tokens"
            value={metrics.tokensUsed.toLocaleString()}
            colorClass="text-cyan-500"
            bgClass="bg-cyan-500/10"
          />
        )}
        
        {cost && (
          <MetricCard 
            icon={DollarSign}
            label="Cost"
            value={formatCost(cost.cost.total)}
            subValue={cost.input_tokens && cost.output_tokens ? `${(cost.input_tokens.total + cost.output_tokens.total).toLocaleString()} tokens` : cost.duration_seconds ? `${Math.ceil(cost.duration_seconds / 60)} min` : undefined}
            colorClass="text-emerald-500"
            bgClass="bg-emerald-500/10"
          />
        )}
      </div>
      
      {/* Export buttons */}
      {onExportTranscript && (
        <div className="flex items-center gap-2 px-4">
          <span className="text-xs text-muted-foreground mr-2">Export:</span>
          <button
            onClick={() => onExportTranscript('txt')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-muted hover:bg-muted/80 transition-colors"
            title="Export as TXT"
          >
            <FileText className="h-3.5 w-3.5" />
            TXT
          </button>
          <button
            onClick={() => onExportTranscript('json')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-muted hover:bg-muted/80 transition-colors"
            title="Export as JSON"
          >
            <FileJson className="h-3.5 w-3.5" />
            JSON
          </button>
          <button
            onClick={() => onExportTranscript('pdf')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors"
            title="Export as PDF"
          >
            <Download className="h-3.5 w-3.5" />
            PDF
          </button>
        </div>
      )}
      
      {/* Active indicator */}
      {isActive && (
        <div className="flex items-center gap-2 px-4 border-l border-border">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          <span className="text-xs font-medium text-red-500">LIVE</span>
        </div>
      )}
    </div>
  );
}

// Compact version for smaller spaces
export function CallMetricsCompact({ 
  metrics,
  cost,
  isActive = false,
  className 
}: Omit<CallMetricsBarProps, 'onExportTranscript'>) {
  return (
    <div className={cn(
      'flex items-center gap-4 text-xs',
      className
    )}>
      {isActive && (
        <span className="flex items-center gap-1.5 text-red-500 font-medium">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          LIVE
        </span>
      )}
      
      <span className="flex items-center gap-1 text-muted-foreground">
        <Clock className="h-3 w-3" />
        {formatDuration(metrics.duration)}
      </span>
      
      <span className={cn(
        'flex items-center gap-1',
        metrics.latency < 500 ? 'text-green-500' : 
        metrics.latency < 1000 ? 'text-yellow-500' : 'text-red-500'
      )}>
        <Zap className="h-3 w-3" />
        {formatLatency(metrics.latency)}
      </span>
      
      <span className="flex items-center gap-1 text-muted-foreground">
        <MessageSquare className="h-3 w-3" />
        {metrics.turnCount} turns
      </span>
      
      {metrics.interrupts > 0 && (
        <span className="flex items-center gap-1 text-orange-500">
          <AlertTriangle className="h-3 w-3" />
          {metrics.interrupts}
        </span>
      )}
      
      {cost && (
        <span className="flex items-center gap-1 text-emerald-500 font-medium">
          <DollarSign className="h-3 w-3" />
          {formatCost(cost.cost.total)}
        </span>
      )}
    </div>
  );
}
