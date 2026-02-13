'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Wand2,
  Copy,
  Check,
  Bot,
  Trash2,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  Sparkles,
  Lightbulb,
  Save,
  History,
  X,
} from 'lucide-react';

import { API_V1 as API_BASE } from '@/lib/api';

// ─── Types ───────────────────────────────────────────────────────

interface PromptHistoryItem {
  id: number;
  title: string;
  provider: string;
  agent_type: string | null;
  language: string;
  description: string | null;
  generated_prompt: string;
  applied_to_agent_id: number | null;
  applied_to_agent_name: string | null;
  created_at: string;
}

interface AgentOption {
  id: number;
  name: string;
  provider: string;
}

// ─── Constants ───────────────────────────────────────────────────

const PROVIDERS = [
  {
    id: 'openai',
    label: 'OpenAI Realtime',
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    desc: 'Token-based, short & concise prompts, GPT-4o models',
  },
  {
    id: 'ultravox',
    label: 'Ultravox',
    color: 'text-violet-500',
    bg: 'bg-violet-500/10',
    border: 'border-violet-500/30',
    desc: 'Llama 3.3 based, detailed prompts, template variables',
  },
  {
    id: 'xai',
    label: 'xAI Grok',
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    desc: 'Conversational, personality-focused, OpenAI-compatible',
  },
  {
    id: 'gemini',
    label: 'Gemini Live',
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    desc: 'Structured, safety-focused, native audio, Gemini 2.0',
  },
] as const;

const AGENT_TYPES = [
  { id: 'sales', label: 'Sales' },
  { id: 'support', label: 'Customer Support' },
  { id: 'collection', label: 'Collections' },
  { id: 'appointment', label: 'Appointment' },
  { id: 'survey', label: 'Survey' },
] as const;

const TONES = [
  { id: 'professional', label: 'Professional' },
  { id: 'friendly', label: 'Friendly' },
  { id: 'formal', label: 'Formal' },
  { id: 'casual', label: 'Casual' },
] as const;

const LANGUAGES = [
  { id: 'en', label: 'English' },
  { id: 'tr', label: 'Turkish' },
  { id: 'de', label: 'German' },
  { id: 'fr', label: 'French' },
  { id: 'es', label: 'Spanish' },
  { id: 'ar', label: 'Arabic' },
  { id: 'nl', label: 'Dutch' },
] as const;

// ─── Helpers ─────────────────────────────────────────────────────

function getToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('access_token') || '';
  }
  return '';
}

const authHeaders = (): Record<string, string> => ({
  Authorization: `Bearer ${getToken()}`,
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

function getProviderConfig(id: string): (typeof PROVIDERS)[number] {
  return PROVIDERS.find((p) => p.id === id) || PROVIDERS[0];
}

// ─── Page Component ──────────────────────────────────────────────

export default function PromptMakerPage(): React.ReactElement {
  // Form state
  const [provider, setProvider] = useState('openai');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [agentType, setAgentType] = useState('');
  const [tone, setTone] = useState('professional');
  const [language, setLanguage] = useState('en');
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [toolsDescription, setToolsDescription] = useState('');
  const [constraints, setConstraints] = useState('');
  const [exampleDialogue, setExampleDialogue] = useState('');

  // UI state
  const [generating, setGenerating] = useState(false);
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [tips, setTips] = useState<string[]>([]);
  const [generatedId, setGeneratedId] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<PromptHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expandedHistoryId, setExpandedHistoryId] = useState<number | null>(null);

  // Apply to agent modal
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [applyPromptId, setApplyPromptId] = useState<number | null>(null);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [applying, setApplying] = useState(false);
  const [applySuccess, setApplySuccess] = useState('');

  // ── Load history ───────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/prompt-maker/history?page_size=50`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.items);
        setHistoryTotal(data.total);
      }
    } catch {
      // ignore
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  // ── Load agents for apply modal ────────────────────────────────
  const loadAgents = useCallback(async () => {
    setAgentsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/agents/`, { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        const list: AgentOption[] = (data.agents || data || []).map(
          (a: { id: number; name: string; provider?: string }) => ({
            id: a.id,
            name: a.name,
            provider: a.provider || 'openai',
          }),
        );
        setAgents(list);
      }
    } catch {
      // ignore
    } finally {
      setAgentsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // ── Generate prompt ────────────────────────────────────────────
  const handleGenerate = async (): Promise<void> => {
    if (!title.trim() || !description.trim()) return;

    setGenerating(true);
    setGeneratedPrompt('');
    setTips([]);
    setGeneratedId(null);

    try {
      const res = await fetch(`${API_BASE}/prompt-maker/generate`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          provider,
          title: title.trim(),
          description: description.trim(),
          agent_type: agentType || null,
          tone,
          language,
          company_name: companyName.trim() || null,
          industry: industry.trim() || null,
          tools_description: toolsDescription.trim() || null,
          constraints: constraints.trim() || null,
          example_dialogue: exampleDialogue.trim() || null,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Generation failed');
      }

      const data = await res.json();
      setGeneratedPrompt(data.generated_prompt);
      setTips(data.tips || []);
      setGeneratedId(data.id);

      // Refresh history
      loadHistory();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to generate prompt');
    } finally {
      setGenerating(false);
    }
  };

  // ── Copy to clipboard ─────────────────────────────────────────
  const handleCopy = async (text: string): Promise<void> => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Delete from history ────────────────────────────────────────
  const handleDelete = async (id: number): Promise<void> => {
    if (!confirm('Delete this prompt?')) return;
    try {
      await fetch(`${API_BASE}/prompt-maker/history/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      setHistory((prev) => prev.filter((h) => h.id !== id));
      setHistoryTotal((prev) => prev - 1);
      if (generatedId === id) {
        setGeneratedPrompt('');
        setGeneratedId(null);
      }
    } catch {
      // ignore
    }
  };

  // ── Open apply modal ──────────────────────────────────────────
  const openApplyModal = (promptId: number): void => {
    setApplyPromptId(promptId);
    setSelectedAgentId(null);
    setApplySuccess('');
    setShowApplyModal(true);
    loadAgents();
  };

  // ── Apply prompt to agent ─────────────────────────────────────
  const handleApply = async (): Promise<void> => {
    if (!applyPromptId || !selectedAgentId) return;

    setApplying(true);
    try {
      const res = await fetch(
        `${API_BASE}/prompt-maker/history/${applyPromptId}/apply`,
        {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ agent_id: selectedAgentId }),
        },
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Apply failed');
      }

      const data = await res.json();
      setApplySuccess(data.message || 'Prompt applied successfully');
      loadHistory();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to apply prompt');
    } finally {
      setApplying(false);
    }
  };

  // ── Provider badge ─────────────────────────────────────────────
  const providerCfg = getProviderConfig(provider);

  return (
    <div className="min-h-screen">
      <Header title="Prompt Maker" description="Generate provider-optimized voice agent prompts" />

      <div className="p-6 space-y-8 max-w-7xl mx-auto">
        {/* ── Title ─────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Wand2 className="h-6 w-6 text-primary-500" />
              Prompt Maker
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              AI-powered prompt generation optimized for each voice provider
            </p>
          </div>
          <button
            onClick={() => {
              setShowHistory(!showHistory);
              if (!showHistory) loadHistory();
            }}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors',
              showHistory
                ? 'bg-primary-500 text-white border-primary-500'
                : 'bg-background border-border hover:bg-muted',
            )}
          >
            <History className="h-4 w-4" />
            History ({historyTotal})
          </button>
        </div>

        <div className={cn('grid gap-8', showHistory ? 'grid-cols-1 lg:grid-cols-3' : 'grid-cols-1')}>
          {/* ── LEFT: Form ──────────────────────────────────────── */}
          <div className={cn(showHistory ? 'lg:col-span-2' : '')}>
            <div className="space-y-6">
              {/* Provider Selection */}
              <div>
                <label className="block text-sm font-semibold mb-3">Select Provider</label>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {PROVIDERS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setProvider(p.id)}
                      className={cn(
                        'relative p-4 rounded-xl border-2 transition-all text-left',
                        provider === p.id
                          ? `${p.border} ${p.bg} ring-2 ring-offset-2 ring-offset-background`
                          : 'border-border hover:border-muted-foreground/30',
                        provider === p.id && p.id === 'openai' && 'ring-emerald-500/50',
                        provider === p.id && p.id === 'ultravox' && 'ring-violet-500/50',
                        provider === p.id && p.id === 'xai' && 'ring-blue-500/50',
                        provider === p.id && p.id === 'gemini' && 'ring-amber-500/50',
                      )}
                    >
                      <div className={cn('font-semibold text-sm', provider === p.id ? p.color : '')}>
                        {p.label}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{p.desc}</div>
                      {provider === p.id && (
                        <div
                          className={cn(
                            'absolute top-2 right-2 h-2 w-2 rounded-full',
                            p.id === 'openai' && 'bg-emerald-500',
                            p.id === 'ultravox' && 'bg-violet-500',
                            p.id === 'xai' && 'bg-blue-500',
                            p.id === 'gemini' && 'bg-amber-500',
                          )}
                        />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Title + Agent Type Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">
                    Prompt Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Healthcare Appointment Scheduler"
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Agent Type</label>
                  <select
                    value={agentType}
                    onChange={(e) => setAgentType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
                  >
                    <option value="">-- Select --</option>
                    {AGENT_TYPES.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium mb-1.5">
                  Description <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  placeholder="Describe what your voice agent should do. Be specific about the workflow, what information to collect, and how to handle different situations..."
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none resize-none"
                />
              </div>

              {/* Tone + Language + Company Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1.5">Tone</label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
                  >
                    {TONES.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
                  >
                    {LANGUAGES.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1.5">Company Name</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Optional"
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Advanced Fields (collapsible) */}
              <AdvancedFields
                industry={industry}
                setIndustry={setIndustry}
                toolsDescription={toolsDescription}
                setToolsDescription={setToolsDescription}
                constraints={constraints}
                setConstraints={setConstraints}
                exampleDialogue={exampleDialogue}
                setExampleDialogue={setExampleDialogue}
              />

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={generating || !title.trim() || !description.trim()}
                className={cn(
                  'w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl',
                  'font-semibold text-white transition-all',
                  generating || !title.trim() || !description.trim()
                    ? 'bg-muted text-muted-foreground cursor-not-allowed'
                    : 'bg-gradient-to-r from-primary-500 to-secondary-500 hover:shadow-lg hover:shadow-primary-500/25',
                )}
              >
                {generating ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Generating for {providerCfg.label}...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5" />
                    Generate {providerCfg.label} Prompt
                  </>
                )}
              </button>

              {/* Generated Result */}
              {generatedPrompt && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Check className="h-5 w-5 text-green-500" />
                      Generated Prompt
                      <span
                        className={cn(
                          'text-xs px-2 py-0.5 rounded-full',
                          providerCfg.bg,
                          providerCfg.color,
                        )}
                      >
                        {providerCfg.label}
                      </span>
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopy(generatedPrompt)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:bg-muted transition-colors text-sm"
                      >
                        {copied ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-green-500" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            Copy
                          </>
                        )}
                      </button>
                      {generatedId && (
                        <button
                          onClick={() => openApplyModal(generatedId)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm"
                        >
                          <Save className="h-3.5 w-3.5" />
                          Save to Agent
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="relative">
                    <pre className="p-4 rounded-xl bg-card border border-border text-sm whitespace-pre-wrap font-mono max-h-[600px] overflow-y-auto custom-scrollbar">
                      {generatedPrompt}
                    </pre>
                  </div>

                  {/* Tips */}
                  {tips.length > 0 && (
                    <div className={cn('p-4 rounded-xl border', providerCfg.bg, providerCfg.border)}>
                      <h4 className={cn('text-sm font-semibold mb-2 flex items-center gap-2', providerCfg.color)}>
                        <Lightbulb className="h-4 w-4" />
                        {providerCfg.label} Tips
                      </h4>
                      <ul className="space-y-1">
                        {tips.map((tip, i) => (
                          <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                            <span className={cn('mt-1 h-1.5 w-1.5 rounded-full flex-shrink-0', providerCfg.color.replace('text-', 'bg-'))} />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: History Panel ────────────────────────────── */}
          {showHistory && (
            <div className="lg:col-span-1">
              <div className="sticky top-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Prompt History
                </h3>

                {historyLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : history.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No prompts generated yet
                  </p>
                ) : (
                  <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto custom-scrollbar pr-1">
                    {history.map((item) => {
                      const cfg = getProviderConfig(item.provider);
                      const isExpanded = expandedHistoryId === item.id;
                      return (
                        <div
                          key={item.id}
                          className="rounded-xl border border-border bg-card overflow-hidden"
                        >
                          {/* Header */}
                          <button
                            onClick={() => setExpandedHistoryId(isExpanded ? null : item.id)}
                            className="w-full p-3 text-left flex items-start justify-between gap-2 hover:bg-muted/50 transition-colors"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={cn('text-xs px-1.5 py-0.5 rounded', cfg.bg, cfg.color)}>
                                  {cfg.label}
                                </span>
                                {item.applied_to_agent_name && (
                                  <span className="text-xs text-green-500 flex items-center gap-1">
                                    <Bot className="h-3 w-3" />
                                    {item.applied_to_agent_name}
                                  </span>
                                )}
                              </div>
                              <p className="text-sm font-medium mt-1 truncate">{item.title}</p>
                              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                                <Clock className="h-3 w-3" />
                                {formatDate(item.created_at)}
                              </p>
                            </div>
                            {isExpanded ? (
                              <ChevronUp className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                            )}
                          </button>

                          {/* Expanded content */}
                          {isExpanded && (
                            <div className="border-t border-border p-3 space-y-3">
                              <pre className="text-xs whitespace-pre-wrap font-mono bg-background p-3 rounded-lg max-h-64 overflow-y-auto custom-scrollbar">
                                {item.generated_prompt}
                              </pre>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleCopy(item.generated_prompt)}
                                  className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-border hover:bg-muted transition-colors"
                                >
                                  <Copy className="h-3 w-3" />
                                  Copy
                                </button>
                                <button
                                  onClick={() => openApplyModal(item.id)}
                                  className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-primary-500 text-white hover:bg-primary-600 transition-colors"
                                >
                                  <Save className="h-3 w-3" />
                                  Save to Agent
                                </button>
                                <button
                                  onClick={() => handleDelete(item.id)}
                                  className="flex items-center gap-1 px-2 py-1 rounded text-xs border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors ml-auto"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Apply to Agent Modal ──────────────────────────────── */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Bot className="h-5 w-5 text-primary-500" />
                Save to Agent
              </h3>
              <button
                onClick={() => setShowApplyModal(false)}
                className="p-1.5 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {applySuccess ? (
                <div className="text-center py-6">
                  <Check className="h-12 w-12 text-green-500 mx-auto mb-3" />
                  <p className="text-sm font-medium">{applySuccess}</p>
                  <button
                    onClick={() => setShowApplyModal(false)}
                    className="mt-4 px-4 py-2 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm"
                  >
                    Close
                  </button>
                </div>
              ) : agentsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : agents.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  No agents found. Create an agent first.
                </p>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    Select an agent to apply this prompt to. The agent&apos;s existing prompt will be replaced.
                  </p>
                  <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                    {agents.map((agent) => {
                      const aCfg = getProviderConfig(agent.provider);
                      return (
                        <button
                          key={agent.id}
                          onClick={() => setSelectedAgentId(agent.id)}
                          className={cn(
                            'w-full flex items-center justify-between p-3 rounded-xl border-2 transition-all text-left',
                            selectedAgentId === agent.id
                              ? 'border-primary-500 bg-primary-500/5'
                              : 'border-border hover:border-muted-foreground/30',
                          )}
                        >
                          <div className="flex items-center gap-3">
                            <Bot className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <p className="text-sm font-medium">{agent.name}</p>
                              <span className={cn('text-xs', aCfg.color)}>{aCfg.label}</span>
                            </div>
                          </div>
                          {selectedAgentId === agent.id && (
                            <Check className="h-5 w-5 text-primary-500" />
                          )}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    onClick={handleApply}
                    disabled={!selectedAgentId || applying}
                    className={cn(
                      'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-colors',
                      !selectedAgentId || applying
                        ? 'bg-muted text-muted-foreground cursor-not-allowed'
                        : 'bg-primary-500 text-white hover:bg-primary-600',
                    )}
                  >
                    {applying ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Applying...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Apply Prompt
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Advanced Fields (Collapsible) ───────────────────────────────

interface AdvancedFieldsProps {
  industry: string;
  setIndustry: (v: string) => void;
  toolsDescription: string;
  setToolsDescription: (v: string) => void;
  constraints: string;
  setConstraints: (v: string) => void;
  exampleDialogue: string;
  setExampleDialogue: (v: string) => void;
}

function AdvancedFields({
  industry,
  setIndustry,
  toolsDescription,
  setToolsDescription,
  constraints,
  setConstraints,
  exampleDialogue,
  setExampleDialogue,
}: AdvancedFieldsProps): React.ReactElement {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-border rounded-xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors"
      >
        <span className="text-sm font-medium">Advanced Options</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {open && (
        <div className="p-4 pt-0 space-y-4 border-t border-border">
          <div>
            <label className="block text-sm font-medium mb-1.5">Industry / Sector</label>
            <input
              type="text"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g. Healthcare, Real Estate, Finance..."
              className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Tools Description</label>
            <textarea
              value={toolsDescription}
              onChange={(e) => setToolsDescription(e.target.value)}
              rows={2}
              placeholder="Describe tools the agent should use (e.g. 'book_appointment', 'lookup_customer', 'transfer_call')"
              className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none resize-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Constraints</label>
            <textarea
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              rows={2}
              placeholder="Things the agent should NEVER do..."
              className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none resize-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Example Dialogue</label>
            <textarea
              value={exampleDialogue}
              onChange={(e) => setExampleDialogue(e.target.value)}
              rows={3}
              placeholder="Agent: Hi, this is Sarah from ABC Clinic...&#10;Customer: Yes, I'd like to schedule an appointment..."
              className="w-full px-3 py-2 rounded-lg bg-background border border-border focus:border-primary-500 focus:outline-none resize-none"
            />
          </div>
        </div>
      )}
    </div>
  );
}
