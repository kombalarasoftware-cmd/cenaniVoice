'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3, TrendingUp, TrendingDown, Minus,
  ThumbsUp, ThumbsDown, Star, Tag,
  FileText, Activity, Users, Calendar, Filter,
  ChevronDown, ChevronRight, Eye, Clock,
  AlertCircle, CheckCircle, Phone, Bot,
  Smile, Meh, Frown, ArrowUpRight,
  Loader2, RefreshCw,
} from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';

// ─── Types ───────────────────────────────────────────────────────
interface AiOverview {
  period_days: number;
  total_calls: number;
  sentiment: { positive: number; neutral: number; negative: number; unset: number };
  quality_score: {
    average: number; min: number; max: number; total_scored: number;
    distribution: Record<string, number>;
  };
  tags: { total_unique: number; total_tagged_calls: number; top_tags: { tag: string; count: number }[] };
  callbacks: { total: number; pending: number; completed: number };
  summaries: { with_summary: number; without_summary: number; coverage_percent: number };
  satisfaction: { positive: number; neutral: number; negative: number };
}

interface SentimentDay {
  date: string; positive: number; neutral: number; negative: number; total: number;
}

interface QualityDay {
  date: string; avg_score: number; min_score: number; max_score: number;
  total_calls: number; scored_calls: number;
}

interface TagItem {
  tag: string; count: number; percentage: number;
  sentiment_breakdown: { positive: number; neutral: number; negative: number };
}

interface CallbackItem {
  call_id: number; call_sid: string; customer_name: string; phone_number: string;
  scheduled_at: string | null; status: string; reason: string; notes: string;
  original_sentiment: string; campaign_name: string;
}

interface AgentComparison {
  agent_id: number; agent_name: string; total_calls: number;
  avg_quality_score: number; positive_sentiment_rate: number; negative_sentiment_rate: number;
  summary_coverage: number; callback_rate: number; avg_duration: number;
}

// ─── Helpers ─────────────────────────────────────────────────────
function getToken() {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token') || '';
  }
  return '';
}

const headers = () => ({
  'Authorization': `Bearer ${getToken()}`,
  'Content-Type': 'application/json',
});

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { day: '2-digit', month: 'short' });
}

function formatDateTime(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ─── Mini Bar Chart (using CSS) ──────────────────────────────────
function BarSegment({ value, max, color, label }: { value: number; max: number; color: string; label: string }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-20 text-right text-muted-foreground">{label}</span>
      <div className="flex-1 h-6 bg-muted rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-500', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-10 font-medium">{value}</span>
    </div>
  );
}

// ─── Stat Card ───────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, subtext, color }: {
  icon: any; label: string; value: string | number; subtext?: string; color: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={cn('flex h-9 w-9 items-center justify-center rounded-lg', color)}>
          <Icon className="h-4 w-4" />
        </div>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {subtext && <p className="text-xs text-muted-foreground mt-1">{subtext}</p>}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────
export default function ReportsPage() {
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'sentiment' | 'quality' | 'tags' | 'callbacks' | 'agents'>('overview');

  // Data states
  const [overview, setOverview] = useState<AiOverview | null>(null);
  const [sentimentTrend, setSentimentTrend] = useState<SentimentDay[]>([]);
  const [qualityTrend, setQualityTrend] = useState<QualityDay[]>([]);
  const [tagsData, setTagsData] = useState<{ total_unique_tags: number; tags: TagItem[] } | null>(null);
  const [callbacks, setCallbacks] = useState<{ stats: Record<string, number>; total: number; callbacks: CallbackItem[] } | null>(null);
  const [agentComparison, setAgentComparison] = useState<AgentComparison[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, stRes, qtRes, tgRes, cbRes, agRes] = await Promise.all([
        fetch(`${API_BASE}/reports/ai/overview?days=${days}`, { headers: headers() }),
        fetch(`${API_BASE}/reports/ai/sentiment-trend?days=${days}`, { headers: headers() }),
        fetch(`${API_BASE}/reports/ai/quality-trend?days=${days}`, { headers: headers() }),
        fetch(`${API_BASE}/reports/ai/tags-distribution?days=${days}`, { headers: headers() }),
        fetch(`${API_BASE}/reports/ai/callbacks?days=${days}`, { headers: headers() }),
        fetch(`${API_BASE}/reports/ai/agent-comparison?days=${days}`, { headers: headers() }),
      ]);

      if (ovRes.ok) setOverview(await ovRes.json());
      if (stRes.ok) setSentimentTrend(await stRes.json());
      if (qtRes.ok) setQualityTrend(await qtRes.json());
      if (tgRes.ok) setTagsData(await tgRes.json());
      if (cbRes.ok) setCallbacks(await cbRes.json());
      if (agRes.ok) setAgentComparison(await agRes.json());
    } catch (err) {
      console.error('Report fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const tabs = [
    { key: 'overview', label: 'Overview', icon: BarChart3 },
    { key: 'sentiment', label: 'Sentiment', icon: Smile },
    { key: 'quality', label: 'Quality Score', icon: Star },
    { key: 'tags', label: 'Tags', icon: Tag },
    { key: 'callbacks', label: 'Callbacks', icon: Phone },
    { key: 'agents', label: 'Agent Comparison', icon: Bot },
  ] as const;

  return (
    <div className="min-h-screen">
      <Header
        title="AI Reports"
        description="Call analysis, sentiment, quality score and more"
      />

      <div className="p-6 space-y-6">
        {/* Period Selector + Refresh */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {[7, 14, 30, 90].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  days === d
                    ? 'bg-primary-500 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                )}
              >
                {d} Days
              </button>
            ))}
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted hover:bg-muted/80 text-sm"
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
            Refresh
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-1 bg-muted rounded-xl overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap',
                activeTab === tab.key
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : (
          <>
            {/* OVERVIEW TAB */}
            {activeTab === 'overview' && overview && <OverviewTab overview={overview} />}

            {/* SENTIMENT TAB */}
            {activeTab === 'sentiment' && <SentimentTab data={sentimentTrend} overview={overview} />}

            {/* QUALITY TAB */}
            {activeTab === 'quality' && <QualityTab data={qualityTrend} overview={overview} />}

            {/* TAGS TAB */}
            {activeTab === 'tags' && tagsData && <TagsTab data={tagsData} />}

            {/* CALLBACKS TAB */}
            {activeTab === 'callbacks' && callbacks && <CallbacksTab data={callbacks} />}

            {/* AGENTS TAB */}
            {activeTab === 'agents' && <AgentsTab data={agentComparison} />}
          </>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TAB COMPONENTS
// ═══════════════════════════════════════════════════════════════════

function OverviewTab({ overview }: { overview: AiOverview }) {
  const sentTotal = overview.sentiment.positive + overview.sentiment.neutral + overview.sentiment.negative;
  const satTotal = overview.satisfaction.positive + overview.satisfaction.neutral + overview.satisfaction.negative;

  return (
    <div className="space-y-6">
      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Phone}
          label="Total Calls"
          value={overview.total_calls}
          subtext={`${overview.period_days} day period`}
          color="bg-blue-500/10 text-blue-500"
        />
        <StatCard
          icon={Star}
          label="Avg. Quality Score"
          value={`${overview.quality_score.average}/100`}
          subtext={`${overview.quality_score.total_scored} calls scored`}
          color={cn(
            overview.quality_score.average >= 70 ? 'bg-green-500/10 text-green-500' :
            overview.quality_score.average >= 40 ? 'bg-amber-500/10 text-amber-500' :
            'bg-red-500/10 text-red-500'
          )}
        />
        <StatCard
          icon={FileText}
          label="Summary Coverage"
          value={`${overview.summaries.coverage_percent}%`}
          subtext={`${overview.summaries.with_summary} / ${overview.total_calls} calls`}
          color="bg-purple-500/10 text-purple-500"
        />
        <StatCard
          icon={Phone}
          label="Callbacks"
          value={overview.callbacks.total}
          subtext={`${overview.callbacks.pending} pending, ${overview.callbacks.completed} completed`}
          color="bg-orange-500/10 text-orange-500"
        />
      </div>

      {/* Sentiment + Satisfaction */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment Distribution */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Smile className="h-5 w-5 text-primary-500" />
            Sentiment Distribution
          </h3>
          <div className="space-y-3">
            <BarSegment value={overview.sentiment.positive} max={sentTotal} color="bg-green-500" label="Positive" />
            <BarSegment value={overview.sentiment.neutral} max={sentTotal} color="bg-gray-400" label="Neutral" />
            <BarSegment value={overview.sentiment.negative} max={sentTotal} color="bg-red-500" label="Negative" />
            {overview.sentiment.unset > 0 && (
              <BarSegment value={overview.sentiment.unset} max={sentTotal + overview.sentiment.unset} color="bg-gray-200" label="Unknown" />
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-border flex justify-between text-sm">
            <span className="text-muted-foreground">Positivity Rate</span>
            <span className="font-bold text-green-500">
              {sentTotal > 0 ? Math.round(overview.sentiment.positive / sentTotal * 100) : 0}%
            </span>
          </div>
        </div>

        {/* Customer Satisfaction */}
        <div className="rounded-xl border border-border bg-card p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Star className="h-5 w-5 text-amber-500" />
            Customer Satisfaction
          </h3>
          <div className="space-y-3">
            <BarSegment value={overview.satisfaction.positive} max={satTotal} color="bg-green-500" label="Satisfied" />
            <BarSegment value={overview.satisfaction.neutral} max={satTotal} color="bg-amber-400" label="Neutral" />
            <BarSegment value={overview.satisfaction.negative} max={satTotal} color="bg-red-500" label="Unsatisfied" />
          </div>
          {/* Quality Score Distribution */}
          <div className="mt-4 pt-3 border-t border-border">
            <p className="text-sm text-muted-foreground mb-2">Quality Score Distribution</p>
            <div className="flex gap-1">
              {Object.entries(overview.quality_score.distribution).map(([range, count]) => {
                const total = overview.quality_score.total_scored || 1;
                const pct = (count / total) * 100;
                const colors: Record<string, string> = {
                  '0-20': 'bg-red-500', '21-40': 'bg-orange-500', '41-60': 'bg-amber-400',
                  '61-80': 'bg-green-400', '81-100': 'bg-green-600',
                };
                return (
                  <div key={range} className="flex-1" title={`${range}: ${count} calls`}>
                    <div className="h-8 bg-muted rounded overflow-hidden flex flex-col justify-end">
                      <div className={cn('rounded', colors[range])} style={{ height: `${Math.max(pct, 4)}%` }} />
                    </div>
                    <p className="text-[10px] text-center mt-1 text-muted-foreground">{range}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Top Tags */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Tag className="h-5 w-5 text-purple-500" />
          Most Used Tags
          <span className="text-sm font-normal text-muted-foreground ml-auto">
            {overview.tags.total_unique} unique tags, {overview.tags.total_tagged_calls} tagged calls
          </span>
        </h3>
        <div className="flex flex-wrap gap-2">
          {overview.tags.top_tags.map((t) => (
            <span
              key={t.tag}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-muted"
            >
              <Tag className="h-3 w-3" />
              {t.tag}
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-primary-500/10 text-primary-500 text-xs font-bold">
                {t.count}
              </span>
            </span>
          ))}
          {overview.tags.top_tags.length === 0 && (
            <p className="text-muted-foreground text-sm">No tags yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Sentiment Tab ───────────────────────────────────────────────
function SentimentTab({ data, overview }: { data: SentimentDay[]; overview: AiOverview | null }) {
  const maxTotal = Math.max(...data.map(d => d.total), 1);
  return (
    <div className="space-y-6">
      {/* Trend Chart (CSS bars) */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="font-semibold mb-4">Daily Sentiment Trend</h3>
        {data.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">No data for this period</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="flex items-end gap-1 min-w-max h-48">
              {data.map((day) => {
                const h = (day.total / maxTotal) * 100;
                const pos = day.total > 0 ? (day.positive / day.total) * h : 0;
                const neu = day.total > 0 ? (day.neutral / day.total) * h : 0;
                const neg = h - pos - neu;
                return (
                  <div key={day.date} className="flex flex-col items-center gap-1 group" title={`${day.date}: +${day.positive} / =${day.neutral} / -${day.negative}`}>
                    <div className="flex flex-col justify-end w-10" style={{ height: '192px' }}>
                      {neg > 0 && <div className="bg-red-500 rounded-t" style={{ height: `${neg}%` }} />}
                      {neu > 0 && <div className="bg-gray-400" style={{ height: `${neu}%` }} />}
                      {pos > 0 && <div className="bg-green-500 rounded-b" style={{ height: `${pos}%` }} />}
                    </div>
                    <span className="text-[10px] text-muted-foreground -rotate-45 origin-top-left whitespace-nowrap">
                      {formatDate(day.date)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500" /> Positive</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-gray-400" /> Neutral</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500" /> Negative</span>
            </div>
          </div>
        )}
      </div>

      {/* Daily Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="text-left p-3 font-medium">Date</th>
              <th className="text-center p-3 font-medium">Total</th>
              <th className="text-center p-3 font-medium text-green-500">Positive</th>
              <th className="text-center p-3 font-medium text-gray-500">Neutral</th>
              <th className="text-center p-3 font-medium text-red-500">Negative</th>
              <th className="text-center p-3 font-medium">Positivity %</th>
            </tr>
          </thead>
          <tbody>
            {data.map((day) => (
              <tr key={day.date} className="border-b border-border hover:bg-muted/30">
                <td className="p-3">{day.date}</td>
                <td className="text-center p-3 font-medium">{day.total}</td>
                <td className="text-center p-3 text-green-500">{day.positive}</td>
                <td className="text-center p-3 text-gray-500">{day.neutral}</td>
                <td className="text-center p-3 text-red-500">{day.negative}</td>
                <td className="text-center p-3 font-bold">
                  {day.total > 0 ? Math.round(day.positive / day.total * 100) : 0}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Quality Tab ─────────────────────────────────────────────────
function QualityTab({ data, overview }: { data: QualityDay[]; overview: AiOverview | null }) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard icon={Star} label="Average" value={overview.quality_score.average}
            color="bg-amber-500/10 text-amber-500" />
          <StatCard icon={TrendingUp} label="Maximum" value={overview.quality_score.max}
            color="bg-green-500/10 text-green-500" />
          <StatCard icon={TrendingDown} label="Minimum" value={overview.quality_score.min}
            color="bg-red-500/10 text-red-500" />
          <StatCard icon={Activity} label="Scored"
            value={`${overview.quality_score.total_scored} / ${overview.total_calls}`}
            color="bg-blue-500/10 text-blue-500" />
        </div>
      )}

      {/* Trend Chart */}
      <div className="rounded-xl border border-border bg-card p-6">
        <h3 className="font-semibold mb-4">Daily Quality Score Trend</h3>
        {data.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">No data for this period</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="flex items-end gap-1 min-w-max h-48">
              {data.map((day) => {
                const h = day.avg_score;
                const color = h >= 70 ? 'bg-green-500' : h >= 40 ? 'bg-amber-400' : 'bg-red-500';
                return (
                  <div key={day.date} className="flex flex-col items-center gap-1 group" title={`${day.date}: ${day.avg_score} (${day.scored_calls} calls)`}>
                    <span className="text-[10px] font-bold opacity-0 group-hover:opacity-100 transition-opacity">{day.avg_score}</span>
                    <div className="flex flex-col justify-end w-10" style={{ height: '170px' }}>
                      <div className={cn('rounded-t', color)} style={{ height: `${h}%` }} />
                    </div>
                    <span className="text-[10px] text-muted-foreground -rotate-45 origin-top-left whitespace-nowrap">
                      {formatDate(day.date)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Daily Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="text-left p-3 font-medium">Date</th>
              <th className="text-center p-3 font-medium">Calls</th>
              <th className="text-center p-3 font-medium">Scored</th>
              <th className="text-center p-3 font-medium">Avg. Score</th>
              <th className="text-center p-3 font-medium">Min</th>
              <th className="text-center p-3 font-medium">Max</th>
            </tr>
          </thead>
          <tbody>
            {data.map((day) => (
              <tr key={day.date} className="border-b border-border hover:bg-muted/30">
                <td className="p-3">{day.date}</td>
                <td className="text-center p-3">{day.total_calls}</td>
                <td className="text-center p-3">{day.scored_calls}</td>
                <td className="text-center p-3">
                  <span className={cn(
                    'px-2 py-0.5 rounded-full text-xs font-bold',
                    day.avg_score >= 70 ? 'bg-green-500/10 text-green-500' :
                    day.avg_score >= 40 ? 'bg-amber-500/10 text-amber-500' :
                    'bg-red-500/10 text-red-500'
                  )}>
                    {day.avg_score}
                  </span>
                </td>
                <td className="text-center p-3 text-muted-foreground">{day.min_score}</td>
                <td className="text-center p-3 text-muted-foreground">{day.max_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Tags Tab ────────────────────────────────────────────────────
function TagsTab({ data }: { data: { total_unique_tags: number; tags: TagItem[] } }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <Tag className="h-5 w-5 text-purple-500" />
          Total {data.total_unique_tags} Unique Tags
        </h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data.tags.map((tag, idx) => (
          <div key={tag.tag} className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-muted-foreground">#{idx + 1}</span>
                <span className="px-2 py-1 rounded-lg bg-muted font-medium">{tag.tag}</span>
              </div>
              <span className="text-lg font-bold">{tag.count}</span>
            </div>
            {/* Sentiment breakdown */}
            <div className="flex gap-1 h-3 rounded-full overflow-hidden bg-muted">
              {tag.count > 0 && (
                <>
                  <div className="bg-green-500" style={{ width: `${(tag.sentiment_breakdown.positive / tag.count) * 100}%` }} />
                  <div className="bg-gray-400" style={{ width: `${(tag.sentiment_breakdown.neutral / tag.count) * 100}%` }} />
                  <div className="bg-red-500" style={{ width: `${(tag.sentiment_breakdown.negative / tag.count) * 100}%` }} />
                </>
              )}
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-muted-foreground">
              <span className="text-green-500">+{tag.sentiment_breakdown.positive}</span>
              <span>={tag.sentiment_breakdown.neutral}</span>
              <span className="text-red-500">-{tag.sentiment_breakdown.negative}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Used in {tag.percentage}% of calls
            </p>
          </div>
        ))}
      </div>
      {data.tags.length === 0 && (
        <p className="text-muted-foreground text-sm py-8 text-center">No tag data yet</p>
      )}
    </div>
  );
}

// ─── Callbacks Tab ───────────────────────────────────────────────
function CallbacksTab({ data }: { data: { stats: Record<string, number>; total: number; callbacks: CallbackItem[] } }) {
  const statusColor: Record<string, string> = {
    pending: 'bg-amber-500/10 text-amber-500',
    completed: 'bg-green-500/10 text-green-500',
    overdue: 'bg-red-500/10 text-red-500',
  };
  const statusLabel: Record<string, string> = {
    pending: 'Pending',
    completed: 'Completed',
    overdue: 'Overdue',
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={Clock} label="Pending" value={data.stats.pending || 0}
          color="bg-amber-500/10 text-amber-500" />
        <StatCard icon={CheckCircle} label="Completed" value={data.stats.completed || 0}
          color="bg-green-500/10 text-green-500" />
        <StatCard icon={AlertCircle} label="Overdue" value={data.stats.overdue || 0}
          color="bg-red-500/10 text-red-500" />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="text-left p-3 font-medium">Customer</th>
              <th className="text-left p-3 font-medium">Phone</th>
              <th className="text-left p-3 font-medium">Date</th>
              <th className="text-left p-3 font-medium">Status</th>
              <th className="text-left p-3 font-medium">Reason</th>
              <th className="text-left p-3 font-medium">Campaign</th>
            </tr>
          </thead>
          <tbody>
            {data.callbacks.map((cb) => (
              <tr key={cb.call_id} className="border-b border-border hover:bg-muted/30">
                <td className="p-3 font-medium">{cb.customer_name || '-'}</td>
                <td className="p-3 text-muted-foreground">{cb.phone_number}</td>
                <td className="p-3">{cb.scheduled_at ? formatDateTime(cb.scheduled_at) : '-'}</td>
                <td className="p-3">
                  <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', statusColor[cb.status] || '')}>
                    {statusLabel[cb.status] || cb.status}
                  </span>
                </td>
                <td className="p-3 text-muted-foreground max-w-48 truncate">{cb.reason || '-'}</td>
                <td className="p-3 text-muted-foreground">{cb.campaign_name || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.callbacks.length === 0 && (
          <p className="text-muted-foreground text-sm py-8 text-center">No callbacks scheduled yet</p>
        )}
      </div>
    </div>
  );
}

// ─── Agents Tab ──────────────────────────────────────────────────
function AgentsTab({ data }: { data: AgentComparison[] }) {
  return (
    <div className="space-y-6">
      <h3 className="font-semibold flex items-center gap-2">
        <Bot className="h-5 w-5 text-primary-500" />
        Agent Performance Comparison
      </h3>

      {data.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">No agent data for this period</p>
      ) : (
        <>
          {/* Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {data.map((agent, idx) => (
              <div key={agent.agent_id} className={cn(
                'rounded-xl border bg-card p-5',
                idx === 0 ? 'border-green-500/50' : 'border-border'
              )}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-xl text-white font-bold',
                      idx === 0 ? 'bg-green-500' : idx === 1 ? 'bg-blue-500' : 'bg-gray-400'
                    )}>
                      {idx + 1}
                    </div>
                    <div>
                      <h4 className="font-semibold">{agent.agent_name}</h4>
                      <p className="text-sm text-muted-foreground">{agent.total_calls} calls</p>
                    </div>
                  </div>
                  <div className={cn(
                    'px-3 py-1.5 rounded-full text-sm font-bold',
                    agent.avg_quality_score >= 70 ? 'bg-green-500/10 text-green-500' :
                    agent.avg_quality_score >= 40 ? 'bg-amber-500/10 text-amber-500' :
                    'bg-red-500/10 text-red-500'
                  )}>
                    <Star className="h-3.5 w-3.5 inline mr-1" />
                    {agent.avg_quality_score}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-2 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Positive Sentiment</p>
                    <p className="font-bold text-green-500">{agent.positive_sentiment_rate}%</p>
                  </div>
                  <div className="p-2 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Negative Sentiment</p>
                    <p className="font-bold text-red-500">{agent.negative_sentiment_rate}%</p>
                  </div>
                  <div className="p-2 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Summary Coverage</p>
                    <p className="font-bold">{agent.summary_coverage}%</p>
                  </div>
                  <div className="p-2 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Callback Rate</p>
                    <p className="font-bold">{agent.callback_rate}%</p>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-border flex justify-between text-sm text-muted-foreground">
                  <span>Avg. Duration: {Math.round(agent.avg_duration)}s</span>
                </div>
              </div>
            ))}
          </div>

          {/* Comparison Table */}
          <div className="rounded-xl border border-border bg-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-3 font-medium">#</th>
                  <th className="text-left p-3 font-medium">Agent</th>
                  <th className="text-center p-3 font-medium">Calls</th>
                  <th className="text-center p-3 font-medium">Quality</th>
                  <th className="text-center p-3 font-medium">Positive %</th>
                  <th className="text-center p-3 font-medium">Negative %</th>
                  <th className="text-center p-3 font-medium">Summary %</th>
                  <th className="text-center p-3 font-medium">Callback %</th>
                  <th className="text-center p-3 font-medium">Avg. Duration</th>
                </tr>
              </thead>
              <tbody>
                {data.map((agent, idx) => (
                  <tr key={agent.agent_id} className="border-b border-border hover:bg-muted/30">
                    <td className="p-3 font-bold">{idx + 1}</td>
                    <td className="p-3 font-medium">{agent.agent_name}</td>
                    <td className="text-center p-3">{agent.total_calls}</td>
                    <td className="text-center p-3">
                      <span className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-bold',
                        agent.avg_quality_score >= 70 ? 'bg-green-500/10 text-green-500' :
                        agent.avg_quality_score >= 40 ? 'bg-amber-500/10 text-amber-500' :
                        'bg-red-500/10 text-red-500'
                      )}>
                        {agent.avg_quality_score}
                      </span>
                    </td>
                    <td className="text-center p-3 text-green-500">{agent.positive_sentiment_rate}%</td>
                    <td className="text-center p-3 text-red-500">{agent.negative_sentiment_rate}%</td>
                    <td className="text-center p-3">{agent.summary_coverage}%</td>
                    <td className="text-center p-3">{agent.callback_rate}%</td>
                    <td className="text-center p-3 text-muted-foreground">{Math.round(agent.avg_duration)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
