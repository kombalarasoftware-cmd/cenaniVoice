'use client';

import { cn } from '@/lib/utils';
import { API_V1 } from '@/lib/api';
import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { toast } from 'sonner';
import {
  ChevronLeft,
  ChevronRight,
  Save,
  Plus,
  Trash2,
  Info,
  Copy,
  Sparkles,
  X,
  Loader2,
  Wand2,
  GitBranch,
} from 'lucide-react';
import Link from 'next/link';
import { LiveConsole } from '@/components/agents/agent-editor';

// ============================================
// Types
// ============================================
type EditorTab = 'prompt' | 'rag' | 'greeting' | 'inactivity' | 'settings' | 'console' | 'lead_capture' | 'call_tags' | 'callback' | 'survey';
type RagSubTab = 'knowledge' | 'sources' | 'documents';
type EndBehavior = 'unspecified' | 'interruptible_hangup' | 'uninterruptible_hangup';
type SurveyQuestionType = 'yes_no' | 'multiple_choice' | 'rating' | 'open_ended';

interface SurveyQuestion {
  id: string;
  type: SurveyQuestionType;
  text: string;
  required: boolean;
  // Multiple choice
  options?: string[];
  allow_multiple?: boolean;
  // Rating
  min_value?: number;
  max_value?: number;
  min_label?: string;
  max_label?: string;
  // Open ended
  max_length?: number;
  placeholder?: string;
  // Branching
  next?: string | null;
  next_on_yes?: string | null;
  next_on_no?: string | null;
  next_by_option?: Record<string, string>;
  next_by_range?: Array<{ min: number; max: number; next: string }>;
}

interface SurveyConfig {
  enabled: boolean;
  questions: SurveyQuestion[];
  start_question?: string | null;
  completion_message: string;
  abort_message: string;
  allow_skip: boolean;
  show_progress: boolean;
}

interface WebSource {
  url: string;
  name: string;
  description: string;
}

interface AgentDocument {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'ready' | 'error';
  error_message?: string;
  chunk_count: number;
  token_count: number;
  created_at: string;
}

interface InactivityMessage {
  id: string;
  duration: number;
  message: string;
  endBehavior: EndBehavior;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

// ============================================
// Helper: Parse Prompt Sections (ElevenLabs Structure)
// ============================================
interface ParsedPromptSections {
  role?: string;        // Personality
  personality?: string; // Environment
  context?: string;     // Tone  
  pronunciations?: string; // Goal
  sample_phrases?: string; // Guardrails
  tools?: string;       // Tools
  rules?: string;       // Character normalization
  flow?: string;        // Error handling
  safety?: string;      // Legacy (merged into guardrails)
}

function parsePromptSections(prompt: string): ParsedPromptSections {
  const sections: ParsedPromptSections = {};
  
  // Define section header patterns (ElevenLabs structure + legacy fallback)
  const sectionPatterns: { key: keyof ParsedPromptSections; patterns: RegExp[] }[] = [
    { key: 'role', patterns: [/^#\s*(Personality|Role\s*&?\s*Objective|Role\s*Definition)/im] },
    { key: 'personality', patterns: [/^#\s*(Environment|Context|Personality\s*&?\s*Tone)/im] },
    { key: 'context', patterns: [/^#\s*(Tone|Context)/im] },
    { key: 'pronunciations', patterns: [/^#\s*(Goal|Steps|Pronunciations?)/im] },
    { key: 'sample_phrases', patterns: [/^#\s*(Guardrails|Rules|Constraints|Sample\s*Phrases?|Example\s*Phrases?)/im] },
    { key: 'tools', patterns: [/^#\s*(Tools?)/im] },
    { key: 'rules', patterns: [/^#\s*(Character\s*normalization|Instructions?|Rules?)/im] },
    { key: 'flow', patterns: [/^#\s*(Error\s*handling|Flow|Process)/im] },
    { key: 'safety', patterns: [/^#\s*(Safety\s*&?\s*Escalation|Safety|Security)/im] },
  ];
  
  const lines = prompt.split('\n');
  let currentSection: keyof ParsedPromptSections | null = null;
  let currentContent: string[] = [];
  
  const saveCurrentSection = () => {
    if (currentSection && currentContent.length > 0) {
      sections[currentSection] = currentContent.join('\n').trim();
    }
    currentContent = [];
  };
  
  for (const line of lines) {
    let foundSection = false;
    
    for (const { key, patterns } of sectionPatterns) {
      for (const pattern of patterns) {
        if (pattern.test(line)) {
          saveCurrentSection();
          currentSection = key;
          foundSection = true;
          break;
        }
      }
      if (foundSection) break;
    }
    
    if (!foundSection && currentSection) {
      currentContent.push(line);
    } else if (!foundSection && !currentSection) {
      // If no section found yet, assume it's all role
      if (!sections.role) {
        currentSection = 'role';
      }
      currentContent.push(line);
    }
  }
  
  saveCurrentSection();
  
  // If nothing was parsed, put everything in role
  if (Object.keys(sections).length === 0 && prompt.trim()) {
    sections.role = prompt.trim();
  }
  
  return sections;
}

// ============================================
// AI Prompt Maker Modal Component
// ============================================
interface PromptMakerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (prompt: string) => void;
  existingPrompt?: string;
}

function PromptMakerModal({ isOpen, onClose, onGenerate, existingPrompt }: PromptMakerModalProps) {
  const [description, setDescription] = useState('');
  const [agentType, setAgentType] = useState('');
  const [tone, setTone] = useState('professional');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [error, setError] = useState('');

  const agentTypes = [
    { id: '', label: 'Select...' },
    { id: 'sales', label: '🛒 Sales Representative' },
    { id: 'appointment', label: '📅 Appointment Assistant' },
    { id: 'support', label: '🎧 Customer Support' },
    { id: 'collection', label: '💰 Collections' },
    { id: 'survey', label: '📋 Survey' },
  ];

  const tones = [
    { id: 'professional', label: 'Professional' },
    { id: 'friendly', label: 'Friendly' },
    { id: 'formal', label: 'Formal' },
    { id: 'casual', label: 'Casual' },
  ];

  const quickSuggestions = [
    'A sales representative for solar energy systems that books appointments',
    'A polite but firm representative that handles debt reminders',
    'A support representative that listens to customer complaints and offers solutions',
    'A concise and to-the-point survey representative',
  ];

  const handleGenerate = async () => {
    if (!description.trim()) {
      setError('Please describe what kind of agent you want');
      return;
    }

    setIsGenerating(true);
    setError('');

    try {
      const response = await fetch(`${API_V1}/prompt-generator/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          agent_type: agentType || undefined,
          tone,
          existing_prompt: existingPrompt || undefined,
          language: 'en',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate prompt');
      }

      const data = await response.json();
      setGeneratedPrompt(data.prompt);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApply = () => {
    onGenerate(generatedPrompt);
    onClose();
    // Reset state
    setDescription('');
    setGeneratedPrompt('');
    setAgentType('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-background rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col border border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">AI Prompt Maker</h2>
              <p className="text-sm text-muted-foreground">
                Describe what you need and AI will generate a professional prompt
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {!generatedPrompt ? (
            <>
              {/* Description Input */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Describe your agent</label>
                <textarea
                  value={description}
                  onChange={(e) => { setDescription(e.target.value); setError(''); }}
                  placeholder="E.g.: A receptionist for a solar energy company. Should respond quickly, warmly, and helpfully to short customer inquiries."
                  rows={4}
                  className="w-full px-4 py-3 bg-muted/30 rounded-xl text-sm border border-border focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
                />
                {error && (
                  <p className="text-sm text-red-500">{error}</p>
                )}
              </div>

              {/* Quick Suggestions */}
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground uppercase tracking-wider">Quick Suggestions</label>
                <div className="flex flex-wrap gap-2">
                  {quickSuggestions.map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setDescription(suggestion)}
                      className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 rounded-lg transition-colors text-left"
                    >
                      {suggestion.length > 50 ? suggestion.substring(0, 50) + '...' : suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Options */}
              <div className="grid grid-cols-2 gap-4">
                {/* Agent Type */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Agent Type (optional)</label>
                  <select
                    value={agentType}
                    onChange={(e) => setAgentType(e.target.value)}
                    className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-violet-500"
                  >
                    {agentTypes.map((type) => (
                      <option key={type.id} value={type.id}>{type.label}</option>
                    ))}
                  </select>
                </div>

                {/* Tone */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Tone</label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-violet-500"
                  >
                    {tones.map((t) => (
                      <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              {existingPrompt && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    💡 Your existing prompt will be improved
                  </p>
                </div>
              )}
            </>
          ) : (
            /* Generated Prompt Preview */
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                <Wand2 className="h-4 w-4" />
                <span>Prompt generated!</span>
              </div>
              <div className="relative">
                <textarea
                  value={generatedPrompt}
                  onChange={(e) => setGeneratedPrompt(e.target.value)}
                  rows={15}
                  className="w-full px-4 py-3 bg-muted/30 rounded-xl text-sm border border-border focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none font-mono"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  You can edit it if you wish
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/30">
          {!generatedPrompt ? (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !description.trim()}
                className={cn(
                  'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all',
                  isGenerating || !description.trim()
                    ? 'bg-muted text-muted-foreground cursor-not-allowed'
                    : 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700 shadow-lg shadow-violet-500/25'
                )}
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Prompt
                  </>
                )}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setGeneratedPrompt('')}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                ← Go Back
              </button>
              <button
                onClick={handleApply}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-sm font-medium transition-colors shadow-lg shadow-emerald-500/25"
              >
                <Wand2 className="h-4 w-4" />
                Apply Prompt
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Suggestions Component
// ============================================
function PromptSuggestions({ onSelect }: { onSelect: (text: string) => void }) {
  const suggestions = [
    'How can my prompt be better?',
    'Rewrite this prompt clearly.',
    'Debug an issue',
  ];

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground uppercase tracking-wider">Suggestions</p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s)}
            className="px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-lg transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Tooltip Component
// ============================================
function Tooltip({ children, content }: { children: React.ReactNode; content: string }) {
  return (
    <div className="group relative inline-flex">
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-foreground text-background text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
        {content}
      </div>
    </div>
  );
}

// ============================================
// Main Page Component
// ============================================
export default function AgentEditorPage() {
  const params = useParams();
  const agentId = params.id as string;
  
  const [activeTab, setActiveTab] = useState<EditorTab>('prompt');
  const [ragSubTab, setRagSubTab] = useState<RagSubTab>('knowledge');
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [agentName, setAgentName] = useState('');
  const [isPromptMakerOpen, setIsPromptMakerOpen] = useState(false);
  const [isTestCallModalOpen, setIsTestCallModalOpen] = useState(false);
  
  // Unified prompt (all sections combined with # headers)
  const [prompt, setPrompt] = useState('');
  
  // Knowledge Base - Static information for the agent
  const [knowledgeBase, setKnowledgeBase] = useState('');
  
  // Web Sources - Dynamic web content sources
  const [webSources, setWebSources] = useState<WebSource[]>([]);
  
  // Documents - Uploaded files for RAG search
  const [documents, setDocuments] = useState<AgentDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Greeting state
  const [firstSpeaker, setFirstSpeaker] = useState<'agent' | 'user'>('agent');
  const [greetingMessage, setGreetingMessage] = useState('');
  const [uninterruptible, setUninterruptible] = useState(false);
  const [firstMessageDelay, setFirstMessageDelay] = useState('');

  // Inactivity Messages state
  const [inactivityMessages, setInactivityMessages] = useState<InactivityMessage[]>([
    { id: '1', duration: 30, message: '', endBehavior: 'unspecified' }
  ]);

  // Settings state
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [selectedModel, setSelectedModel] = useState('gpt-realtime-mini');
  const [selectedLanguage, setSelectedLanguage] = useState('tr');
  const [voiceGenderFilter, setVoiceGenderFilter] = useState<'all' | 'male' | 'female'>('all');
  const [selectedTimezone, setSelectedTimezone] = useState('Europe/Istanbul');
  const [maxDuration, setMaxDuration] = useState(300);
  const [silenceTimeout, setSilenceTimeout] = useState(10);
  const [recordCalls, setRecordCalls] = useState(true);
  const [autoTranscribe, setAutoTranscribe] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  // Advanced Settings state
  const [temperature, setTemperature] = useState(0.7);
  const [vadThreshold, setVadThreshold] = useState(0.5);
  const [turnDetection, setTurnDetection] = useState('server_vad');
  const [vadEagerness, setVadEagerness] = useState('auto');
  const [silenceDurationMs, setSilenceDurationMs] = useState(800);
  const [prefixPaddingMs, setPrefixPaddingMs] = useState(500);
  const [idleTimeoutMs, setIdleTimeoutMs] = useState<number | null>(null);
  const [interruptResponse, setInterruptResponse] = useState(true);
  const [createResponse, setCreateResponse] = useState(true);
  const [noiseReduction, setNoiseReduction] = useState(true);
  const [maxOutputTokens, setMaxOutputTokens] = useState(500);
  const [speechSpeed, setSpeechSpeed] = useState(1.0);
  const [transcriptModel, setTranscriptModel] = useState('gpt-4o-transcribe');

  // Smart Features (Smart Features)
  const [leadCaptureEnabled, setLeadCaptureEnabled] = useState(false);
  const [leadCaptureTriggers, setLeadCaptureTriggers] = useState<string[]>(['interested', 'callback']);
  const [leadCaptureDefaultPriority, setLeadCaptureDefaultPriority] = useState(2);
  const [leadCaptureAutoPhone, setLeadCaptureAutoPhone] = useState(true);
  const [leadCaptureAutoAddress, setLeadCaptureAutoAddress] = useState(false);
  const [leadCaptureRequireConfirmation, setLeadCaptureRequireConfirmation] = useState(true);

  const [callTagsEnabled, setCallTagsEnabled] = useState(false);
  const [callTagsAutoTags, setCallTagsAutoTags] = useState<string[]>([]);
  const [callTagsOnInterest, setCallTagsOnInterest] = useState(true);
  const [callTagsOnRejection, setCallTagsOnRejection] = useState(true);
  const [callTagsOnCallback, setCallTagsOnCallback] = useState(true);

  const [callbackEnabled, setCallbackEnabled] = useState(false);
  const [callbackDefaultDelayHours, setCallbackDefaultDelayHours] = useState(24);
  const [callbackMaxAttempts, setCallbackMaxAttempts] = useState(3);
  const [callbackRespectBusinessHours, setCallbackRespectBusinessHours] = useState(true);
  const [callbackAskPreferredTime, setCallbackAskPreferredTime] = useState(true);

  // Survey state
  const [surveyEnabled, setSurveyEnabled] = useState(false);
  const [surveyQuestions, setSurveyQuestions] = useState<SurveyQuestion[]>([]);
  const [surveyStartQuestion, setSurveyStartQuestion] = useState<string | null>(null);
  const [surveyCompletionMessage, setSurveyCompletionMessage] = useState('Thank you for participating in our survey!');
  const [surveyAbortMessage, setSurveyAbortMessage] = useState('Survey cancelled, glad I could help.');
  const [surveyAllowSkip, setSurveyAllowSkip] = useState(false);
  const [surveyShowProgress, setSurveyShowProgress] = useState(true);
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);

  // Fetch agent data on mount
  useEffect(() => {
    const fetchAgent = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_V1}/agents/${agentId}`, {
          headers,
        });
        
        if (!response.ok) {
          throw new Error('Failed to load agent');
        }
        
        const data = await response.json();
        setAgentName(data.name || '');
        
        // Build unified prompt from sections (ElevenLabs structure)
        const buildUnifiedPrompt = (): string => {
          const parts: string[] = [];
          if (data.prompt_role) parts.push(`# Personality\n${data.prompt_role}`);
          if (data.prompt_personality) parts.push(`# Environment\n${data.prompt_personality}`);
          if (data.prompt_context) parts.push(`# Tone\n${data.prompt_context}`);
          if (data.prompt_pronunciations) parts.push(`# Goal\n${data.prompt_pronunciations}`);
          if (data.prompt_sample_phrases) parts.push(`# Guardrails\n${data.prompt_sample_phrases}`);
          if (data.prompt_tools) parts.push(`# Tools\n${data.prompt_tools}`);
          if (data.prompt_rules) parts.push(`# Character normalization\n${data.prompt_rules}`);
          if (data.prompt_flow) parts.push(`# Error handling\n${data.prompt_flow}`);
          if (data.prompt_safety) parts.push(`# Guardrails (Legacy)\n${data.prompt_safety}`);
          return parts.join('\n\n');
        };
        
        setPrompt(buildUnifiedPrompt());
        setGreetingMessage(data.greeting_message || '');
        setFirstSpeaker(data.first_speaker || 'agent');
        setUninterruptible(data.greeting_uninterruptible ?? false);
        setFirstMessageDelay(data.first_message_delay ? data.first_message_delay.toString() : '');
        setSelectedProvider(data.provider || 'openai');
        setSelectedVoice(data.voice || 'alloy');
        setSelectedModel(data.model_type || 'gpt-realtime-mini');
        setSelectedLanguage(data.language || 'tr');
        setSelectedTimezone(data.timezone || 'Europe/Istanbul');
        setMaxDuration(data.max_duration ?? 300);
        setSilenceTimeout(data.silence_timeout ?? 10);
        setRecordCalls(data.record_calls ?? true);
        setAutoTranscribe(data.auto_transcribe ?? true);
        
        // Load advanced settings
        setTemperature(data.temperature ?? 0.7);
        setVadThreshold(data.vad_threshold ?? 0.3);  // Default: more sensitive
        setTurnDetection(data.turn_detection || 'server_vad');
        setVadEagerness(data.vad_eagerness || 'auto');
        setSilenceDurationMs(data.silence_duration_ms ?? 800);
        setPrefixPaddingMs(data.prefix_padding_ms ?? 500);
        setIdleTimeoutMs(data.idle_timeout_ms ?? null);
        setInterruptResponse(data.interrupt_response ?? true);
        setCreateResponse(data.create_response ?? true);
        setNoiseReduction(data.noise_reduction ?? true);
        setMaxOutputTokens(data.max_output_tokens ?? 500);
        setSpeechSpeed(data.speech_speed ?? 1.0);
        setTranscriptModel(data.transcript_model || 'gpt-4o-transcribe');
        
        // Load inactivity messages
        if (data.inactivity_messages && Array.isArray(data.inactivity_messages)) {
          setInactivityMessages(data.inactivity_messages.map((msg: any, index: number) => ({
            id: (index + 1).toString(),
            duration: msg.duration || 30,
            message: msg.message || '',
            endBehavior: msg.end_behavior || 'unspecified',
          })));
        }
        
        // Load knowledge base
        setKnowledgeBase(data.knowledge_base || '');
        
        // Load web sources
        setWebSources(data.web_sources || []);
        
        // Load smart features (Smart Features)
        if (data.smart_features) {
          const sf = data.smart_features;
          // Lead Capture
          if (sf.lead_capture) {
            setLeadCaptureEnabled(sf.lead_capture.enabled ?? false);
            setLeadCaptureTriggers(sf.lead_capture.triggers || ['interested', 'callback']);
            setLeadCaptureDefaultPriority(sf.lead_capture.default_priority ?? 2);
            setLeadCaptureAutoPhone(sf.lead_capture.auto_capture_phone ?? true);
            setLeadCaptureAutoAddress(sf.lead_capture.auto_capture_address ?? false);
            setLeadCaptureRequireConfirmation(sf.lead_capture.require_confirmation ?? true);
          }
          // Call Tags
          if (sf.call_tags) {
            setCallTagsEnabled(sf.call_tags.enabled ?? false);
            setCallTagsAutoTags(sf.call_tags.auto_tags || []);
            setCallTagsOnInterest(sf.call_tags.tag_on_interest ?? true);
            setCallTagsOnRejection(sf.call_tags.tag_on_rejection ?? true);
            setCallTagsOnCallback(sf.call_tags.tag_on_callback ?? true);
          }
          // Callback
          if (sf.callback) {
            setCallbackEnabled(sf.callback.enabled ?? false);
            setCallbackDefaultDelayHours(sf.callback.default_delay_hours ?? 24);
            setCallbackMaxAttempts(sf.callback.max_attempts ?? 3);
            setCallbackRespectBusinessHours(sf.callback.respect_business_hours ?? true);
            setCallbackAskPreferredTime(sf.callback.ask_preferred_time ?? true);
          }
        }
        
        // Load survey config
        if (data.survey_config) {
          const sc = data.survey_config;
          setSurveyEnabled(sc.enabled ?? false);
          setSurveyQuestions(sc.questions || []);
          setSurveyStartQuestion(sc.start_question || null);
          setSurveyCompletionMessage(sc.completion_message || 'Thank you for participating in our survey!');
          setSurveyAbortMessage(sc.abort_message || 'Survey cancelled, glad I could help.');
          setSurveyAllowSkip(sc.allow_skip ?? false);
          setSurveyShowProgress(sc.show_progress ?? true);
        }
        
        // Load documents list
        try {
          const docsResponse = await fetch(`${API_V1}/agents/${agentId}/documents/`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
          });
          if (docsResponse.ok) {
            const docsData = await docsResponse.json();
            setDocuments(docsData || []);
          }
        } catch (docError) {
          console.error('Documents fetch error:', docError);
        }
      } catch (error) {
        console.error('Agent fetch error:', error);
        toast.error('Error occurred while loading agent');
      } finally {
        setIsLoading(false);
      }
    };

    if (agentId) {
      fetchAgent();
    }
  }, [agentId]);

  const tabs = [
    { id: 'prompt' as EditorTab, label: 'Prompt' },
    { id: 'rag' as EditorTab, label: 'RAG' },
    { id: 'greeting' as EditorTab, label: 'Greeting' },
    { id: 'inactivity' as EditorTab, label: 'Inactivity Messages' },
    { id: 'lead_capture' as EditorTab, label: 'Lead Capture' },
    { id: 'call_tags' as EditorTab, label: 'Call Tags' },
    { id: 'callback' as EditorTab, label: 'Callback' },
    { id: 'survey' as EditorTab, label: 'Survey' },
    { id: 'settings' as EditorTab, label: 'Settings' },
    { id: 'console' as EditorTab, label: 'Console' },
  ];

  const ragSubTabs = [
    { id: 'knowledge' as RagSubTab, label: 'Knowledge Base', icon: '📚' },
    { id: 'sources' as RagSubTab, label: 'Web Sources', icon: '🌐' },
    { id: 'documents' as RagSubTab, label: 'Documents', icon: '📄' },
  ];

  const openaiVoices = [
    { id: 'alloy', name: 'Alloy', gender: 'female', description: 'Neutral, balanced' },
    { id: 'ash', name: 'Ash', gender: 'male', description: 'Confident, clear' },
    { id: 'ballad', name: 'Ballad', gender: 'male', description: 'Warm, deep' },
    { id: 'coral', name: 'Coral', gender: 'female', description: 'Friendly, warm' },
    { id: 'echo', name: 'Echo', gender: 'male', description: 'Deep, resonant' },
    { id: 'sage', name: 'Sage', gender: 'female', description: 'Calm, wise' },
    { id: 'shimmer', name: 'Shimmer', gender: 'female', description: 'Soft, gentle' },
    { id: 'verse', name: 'Verse', gender: 'male', description: 'Dynamic, expressive' },
    { id: 'marin', name: 'Marin ⭐', gender: 'female', description: 'Natural, recommended' },
    { id: 'cedar', name: 'Cedar ⭐', gender: 'male', description: 'Natural, recommended' },
  ];

  const ultravoxVoices = [
    // Turkish
    { id: 'Cicek-Turkish', name: 'Cicek (TR, Female)', gender: 'female' },
    { id: 'Doga-Turkish', name: 'Doga (TR, Male)', gender: 'male' },
    // English
    { id: 'Mark', name: 'Mark (EN, Male)', gender: 'male' },
    { id: 'Jessica', name: 'Jessica (EN, Female)', gender: 'female' },
    { id: 'Sarah', name: 'Sarah (EN, Female)', gender: 'female' },
    { id: 'Alex', name: 'Alex (EN, Male)', gender: 'male' },
    { id: 'Carter', name: 'Carter (EN, Male, Cartesia)', gender: 'male' },
    { id: 'Olivia', name: 'Olivia (EN, Female)', gender: 'female' },
    { id: 'Edward', name: 'Edward (EN, Male)', gender: 'male' },
    { id: 'Luna', name: 'Luna (EN, Female)', gender: 'female' },
    { id: 'Ashley', name: 'Ashley (EN, Female)', gender: 'female' },
    { id: 'Dennis', name: 'Dennis (EN, Male)', gender: 'male' },
    { id: 'Theodore', name: 'Theodore (EN, Male)', gender: 'male' },
    { id: 'Julia', name: 'Julia (EN, Female)', gender: 'female' },
    { id: 'Shaun', name: 'Shaun (EN, Male)', gender: 'male' },
    { id: 'Hana', name: 'Hana (EN, Female)', gender: 'female' },
    { id: 'Blake', name: 'Blake (EN, Male)', gender: 'male' },
    { id: 'Timothy', name: 'Timothy (EN, Male)', gender: 'male' },
    { id: 'Chelsea', name: 'Chelsea (EN, Female)', gender: 'female' },
    { id: 'Emily-English', name: 'Emily (EN, Female)', gender: 'female' },
    { id: 'Aaron-English', name: 'Aaron (EN, Male)', gender: 'male' },
    // German
    { id: 'Josef', name: 'Josef (DE, Male)', gender: 'male' },
    { id: 'Johanna', name: 'Johanna (DE, Female)', gender: 'female' },
    { id: 'Ben-German', name: 'Ben (DE, Male)', gender: 'male' },
    { id: 'Susi-German', name: 'Susi (DE, Female)', gender: 'female' },
    // French
    { id: 'Hugo-French', name: 'Hugo (FR, Male)', gender: 'male' },
    { id: 'Coco-French', name: 'Coco (FR, Female)', gender: 'female' },
    { id: 'Alize-French', name: 'Alize (FR, Female)', gender: 'female' },
    { id: 'Nicolas-French', name: 'Nicolas (FR, Male)', gender: 'male' },
    // Spanish
    { id: 'Alex-Spanish', name: 'Alex (ES, Male)', gender: 'male' },
    { id: 'Andrea-Spanish', name: 'Andrea (ES, Female)', gender: 'female' },
    { id: 'Tatiana-Spanish', name: 'Tatiana (ES, Female)', gender: 'female' },
    { id: 'Mauricio-Spanish', name: 'Mauricio (ES, Male)', gender: 'male' },
    // Italian
    { id: 'Linda-Italian', name: 'Linda (IT, Female)', gender: 'female' },
    { id: 'Giovanni-Italian', name: 'Giovanni (IT, Male)', gender: 'male' },
    // Portuguese
    { id: 'Rosa-Portuguese', name: 'Rosa (PT-BR, Female)', gender: 'female' },
    { id: 'Tiago-Portuguese', name: 'Tiago (PT-BR, Male)', gender: 'male' },
    // Arabic
    { id: 'Salma-Arabic', name: 'Salma (AR, Female)', gender: 'female' },
    { id: 'Raed-Arabic', name: 'Raed (AR-SA, Male)', gender: 'male' },
    // Japanese
    { id: 'Morioki-Japanese', name: 'Morioki (JA, Male)', gender: 'male' },
    { id: 'Asahi-Japanese', name: 'Asahi (JA, Female)', gender: 'female' },
    // Korean
    { id: 'Yoona', name: 'Yoona (KO, Female)', gender: 'female' },
    { id: 'Seojun', name: 'Seojun (KO, Male)', gender: 'male' },
    // Chinese
    { id: 'Maya-Chinese', name: 'Maya (ZH, Female)', gender: 'female' },
    { id: 'Martin-Chinese', name: 'Martin (ZH, Male)', gender: 'male' },
    // Hindi
    { id: 'Riya-Hindi-Urdu', name: 'Riya (HI, Female)', gender: 'female' },
    { id: 'Aakash-Hindi', name: 'Aakash (HI, Male)', gender: 'male' },
    // Russian
    { id: 'Nadia-Russian', name: 'Nadia (RU, Female)', gender: 'female' },
    { id: 'Felix-Russian', name: 'Felix (RU, Male)', gender: 'male' },
    // Dutch
    { id: 'Ruth-Dutch', name: 'Ruth (NL, Female)', gender: 'female' },
    { id: 'Daniel-Dutch', name: 'Daniel (NL, Male)', gender: 'male' },
    // Ukrainian
    { id: 'Vira-Ukrainian', name: 'Vira (UK, Female)', gender: 'female' },
    { id: 'Dmytro-Ukrainian', name: 'Dmytro (UK, Male)', gender: 'male' },
    // Swedish
    { id: 'Sanna-Swedish', name: 'Sanna (SV, Female)', gender: 'female' },
    { id: 'Adam-Swedish', name: 'Adam (SV, Male)', gender: 'male' },
    // Polish
    { id: 'Hanna-Polish', name: 'Hanna (PL, Female)', gender: 'female' },
    { id: 'Marcin-Polish', name: 'Marcin (PL, Male)', gender: 'male' },
  ];

  const pipelineVoices = [
    // Turkish
    { id: 'tr_TR-dfki-medium', name: 'Dfki (TR, Male)', gender: 'male' },
    { id: 'tr_TR-fahrettin-medium', name: 'Fahrettin (TR, Male)', gender: 'male' },
    { id: 'tr_TR-fettah-medium', name: 'Fettah (TR, Male)', gender: 'male' },
    // English
    { id: 'en_US-amy-medium', name: 'Amy (EN, Female)', gender: 'female' },
    { id: 'en_US-lessac-high', name: 'Lessac HQ (EN, Male)', gender: 'male' },
    { id: 'en_US-ryan-high', name: 'Ryan HQ (EN, Male)', gender: 'male' },
    { id: 'en_US-kristin-medium', name: 'Kristin (EN, Female)', gender: 'female' },
    { id: 'en_GB-cori-high', name: 'Cori HQ (EN-GB, Female)', gender: 'female' },
    // German
    { id: 'de_DE-thorsten-medium', name: 'Thorsten (DE, Male)', gender: 'male' },
    { id: 'de_DE-thorsten-high', name: 'Thorsten HQ (DE, Male)', gender: 'male' },
    { id: 'de_DE-thorsten_emotional-medium', name: 'Thorsten Emotional (DE, Male)', gender: 'male' },
    { id: 'de_DE-eva_k-x_low', name: 'Eva (DE, Female)', gender: 'female' },
    { id: 'de_DE-kerstin-low', name: 'Kerstin (DE, Female)', gender: 'female' },
    // French
    { id: 'fr_FR-siwis-medium', name: 'Siwis (FR, Female)', gender: 'female' },
    { id: 'fr_FR-tom-medium', name: 'Tom (FR, Male)', gender: 'male' },
    { id: 'fr_FR-gilles-low', name: 'Gilles (FR, Male)', gender: 'male' },
    // Spanish
    { id: 'es_ES-sharvard-medium', name: 'Sharvard (ES, Male)', gender: 'male' },
    { id: 'es_ES-davefx-medium', name: 'Davefx (ES, Male)', gender: 'male' },
    { id: 'es_MX-claude-high', name: 'Claude HQ (ES-MX, Male)', gender: 'male' },
    // Italian
    { id: 'it_IT-riccardo-x_low', name: 'Riccardo (IT, Male)', gender: 'male' },
    { id: 'it_IT-paola-medium', name: 'Paola (IT, Female)', gender: 'female' },
  ];

  const allVoices = selectedProvider === 'ultravox' ? ultravoxVoices : selectedProvider === 'pipeline' ? pipelineVoices : openaiVoices;
  const voices = voiceGenderFilter === 'all' ? allVoices : allVoices.filter(v => v.gender === voiceGenderFilter);

  const addInactivityMessage = () => {
    setInactivityMessages([
      ...inactivityMessages,
      { id: Date.now().toString(), duration: 30, message: '', endBehavior: 'unspecified' }
    ]);
    setHasChanges(true);
  };

  const removeInactivityMessage = (id: string) => {
    setInactivityMessages(inactivityMessages.filter(m => m.id !== id));
    setHasChanges(true);
  };

  const updateInactivityMessage = (id: string, field: keyof InactivityMessage, value: string | number) => {
    setInactivityMessages(inactivityMessages.map(m => 
      m.id === id ? { ...m, [field]: value } : m
    ));
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!hasChanges) return;
    
    setIsSaving(true);
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Parse unified prompt into sections by # headers (ElevenLabs structure)
      const parseUnifiedPrompt = (unified: string): Record<string, string> => {
        const sections: Record<string, string> = {};
        const lines = unified.split('\n');
        let currentSection = '';
        let currentContent: string[] = [];
        
        for (const line of lines) {
          if (line.startsWith('# ')) {
            // Save previous section
            if (currentSection) {
              sections[currentSection] = currentContent.join('\n').trim();
            }
            // Determine new section (ElevenLabs headers → DB column keys)
            const header = line.substring(2).toLowerCase();
            if (header.includes('personality') && !header.includes('tone')) currentSection = 'role';
            else if (header.includes('environment')) currentSection = 'personality';
            else if (header.includes('tone') || header.includes('üslup')) currentSection = 'context';
            else if (header.includes('goal') || header.includes('hedef')) currentSection = 'pronunciations';
            else if (header.includes('guardrails') || header.includes('kısıtlama')) currentSection = 'sample_phrases';
            else if (header.includes('tool')) currentSection = 'tools';
            else if (header.includes('character') || header.includes('normalization')) currentSection = 'rules';
            else if (header.includes('error') || header.includes('hata')) currentSection = 'flow';
            // Legacy fallback patterns
            else if (header.includes('role') || header.includes('objective')) currentSection = 'role';
            else if (header.includes('instruction') || header.includes('rule')) currentSection = 'rules';
            else if (header.includes('flow')) currentSection = 'flow';
            else if (header.includes('phrase')) currentSection = 'sample_phrases';
            else if (header.includes('safety') || header.includes('escalation')) currentSection = 'sample_phrases'; // merge into guardrails
            else if (header.includes('pronunciation')) currentSection = 'pronunciations';
            else if (header.includes('context')) currentSection = 'context';
            else currentSection = 'role'; // Default
            currentContent = [];
          } else {
            currentContent.push(line);
          }
        }
        // Save last section
        if (currentSection) {
          sections[currentSection] = currentContent.join('\n').trim();
        }
        return sections;
      };

      const promptSections = parseUnifiedPrompt(prompt);

      const response = await fetch(`${API_V1}/agents/${agentId}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          name: agentName,
          prompt: {
            role: promptSections.role || '',
            personality: promptSections.personality || '',
            context: promptSections.context || '',
            pronunciations: promptSections.pronunciations || '',
            sample_phrases: promptSections.sample_phrases || '',
            tools: promptSections.tools || '',
            rules: promptSections.rules || '',
            flow: promptSections.flow || '',
            safety: promptSections.safety || '',
            language: '',  // Legacy field
          },
          provider: selectedProvider,
          voice_settings: {
            model_type: selectedModel,
            voice: selectedVoice,
            language: selectedLanguage,
            timezone: selectedTimezone,
            speech_speed: speechSpeed,
            ...(selectedProvider === 'pipeline' ? { pipeline_voice: selectedVoice } : {}),
          },
          call_settings: {
            max_duration: maxDuration,
            silence_timeout: silenceTimeout,
            max_retries: 3,
            retry_delay: 60,
          },
          behavior_settings: {
            interruptible: !uninterruptible,
            auto_transcribe: autoTranscribe,
            record_calls: recordCalls,
            human_transfer: false,
          },
          advanced_settings: {
            temperature: temperature,
            vad_threshold: vadThreshold,
            turn_detection: turnDetection,
            vad_eagerness: vadEagerness,
            silence_duration_ms: silenceDurationMs,
            prefix_padding_ms: prefixPaddingMs,
            idle_timeout_ms: idleTimeoutMs,
            interrupt_response: interruptResponse,
            create_response: createResponse,
            noise_reduction: noiseReduction,
            max_output_tokens: maxOutputTokens,
            transcript_model: transcriptModel,
          },
          greeting_settings: {
            first_speaker: firstSpeaker,
            greeting_message: greetingMessage,
            greeting_uninterruptible: uninterruptible,
            first_message_delay: parseFloat(firstMessageDelay) || 0,
          },
          inactivity_messages: inactivityMessages.map(msg => ({
            duration: msg.duration,
            message: msg.message,
            end_behavior: msg.endBehavior,
          })),
          knowledge_base: knowledgeBase,
          web_sources: webSources,
          smart_features: {
            lead_capture: {
              enabled: leadCaptureEnabled,
              triggers: leadCaptureTriggers,
              default_priority: leadCaptureDefaultPriority,
              auto_capture_phone: leadCaptureAutoPhone,
              auto_capture_address: leadCaptureAutoAddress,
              require_confirmation: leadCaptureRequireConfirmation,
            },
            call_tags: {
              enabled: callTagsEnabled,
              auto_tags: callTagsAutoTags,
              tag_on_interest: callTagsOnInterest,
              tag_on_rejection: callTagsOnRejection,
              tag_on_callback: callTagsOnCallback,
            },
            callback: {
              enabled: callbackEnabled,
              default_delay_hours: callbackDefaultDelayHours,
              max_attempts: callbackMaxAttempts,
              respect_business_hours: callbackRespectBusinessHours,
              ask_preferred_time: callbackAskPreferredTime,
            },
          },
          survey_config: {
            enabled: surveyEnabled,
            questions: surveyQuestions,
            start_question: surveyStartQuestion || (surveyQuestions.length > 0 ? surveyQuestions[0].id : null),
            completion_message: surveyCompletionMessage,
            abort_message: surveyAbortMessage,
            allow_skip: surveyAllowSkip,
            show_progress: surveyShowProgress,
          },
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save agent');
      }

      toast.success('Agent saved successfully');
      setHasChanges(false);
    } catch (error) {
      console.error('Save error:', error);
      toast.error(error instanceof Error ? error.message : 'An error occurred while saving the agent');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-background border-b border-border">
        <div className="flex h-14 items-center justify-between px-4">
          {/* Left - Agent Name */}
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/agents"
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted transition-colors"
            >
              <ChevronLeft className="h-5 w-5" />
            </Link>
            <input
              type="text"
              value={agentName}
              onChange={(e) => { setAgentName(e.target.value); setHasChanges(true); }}
              className="text-lg font-medium bg-transparent border-none focus:outline-none focus:ring-0"
            />
          </div>

          {/* Center - Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                hasChanges && !isSaving
                  ? 'bg-primary-500 hover:bg-primary-600 text-white'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              )}
            >
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {isSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Editor Panel */}
        <div className="flex-1 flex flex-col border-r border-border">
          {/* Tabs */}
          <div className="flex items-center gap-1 px-4 pt-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors border-b-2',
                  activeTab === tab.id
                    ? 'text-foreground border-primary-500 bg-muted/50'
                    : 'text-muted-foreground border-transparent hover:text-foreground hover:bg-muted/30'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-auto">
            {/* Prompt Tab - Single Unified Editor */}
            {activeTab === 'prompt' && (
              <div className="flex flex-col h-full p-4">
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-medium">System Prompt</h3>
                    <p className="text-xs text-muted-foreground">
                      Separate sections with # headers: Personality, Environment, Tone, Goal, Guardrails, Tools, Character normalization, Error handling
                    </p>
                  </div>
                  <button
                    onClick={() => setIsPromptMakerOpen(true)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white rounded-lg text-sm font-medium transition-all shadow-lg"
                  >
                    <Sparkles className="h-4 w-4" />
                    AI Prompt Maker
                  </button>
                </div>

                {/* Unified Prompt Editor */}
                <textarea
                  value={prompt}
                  onChange={(e) => { setPrompt(e.target.value); setHasChanges(true); }}
                  placeholder={`# Personality
You are a customer representative for [Company Name].
- Professional, friendly, and solution-oriented
- Patient and reliable

# Environment
- Phone-based customer call
- Customer is being called for the first time

# Tone
- Use a warm, professional, and concise tone
- Keep each response to 1-2 sentences. This step is important.
- Vary your acknowledgment phrases, don't repeat the same ones
- Speak in English

# Goal
1. Greet the customer and introduce yourself
2. Explain the purpose of the call
3. Understand the customer's needs. This step is important.
4. Offer a solution and confirm
5. Thank them and end the call

# Guardrails
- Do not provide information on out-of-scope topics. This step is important.
- Do not state information you are not sure about
- Unclear audio: "I'm sorry, could you please repeat that?"

# Tools
## transfer_to_human
**When to use:** When the customer requests a human representative
**Usage:**
1. Inform the customer they will be transferred
2. Call the tool
**Error handling:** If transfer fails, ask them to wait

# Character normalization
- Email: "a-t" → "@", "dot" → "."
- Phone: spell out digits one by one

# Error handling
1. Apologize to the customer
2. Offer an alternative solution
3. Redirect to a human if necessary`}
                  className="flex-1 w-full p-4 bg-muted/30 rounded-xl text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 border border-border leading-relaxed"
                />
              </div>
            )}

            {/* RAG Tab with Sub-tabs */}
            {activeTab === 'rag' && (
              <div className="flex flex-col h-full">
                {/* RAG Sub-tabs */}
                <div className="flex items-center gap-1 px-4 py-3 border-b border-border bg-muted/20">
                  {ragSubTabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setRagSubTab(tab.id)}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                        ragSubTab === tab.id
                          ? 'bg-primary-500 text-white'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                      )}
                    >
                      <span>{tab.icon}</span>
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Knowledge Base Sub-tab */}
                {ragSubTab === 'knowledge' && (
                  <div className="p-6 space-y-6 flex-1 overflow-auto">
                    <div className="flex flex-col h-full">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <h3 className="text-lg font-semibold">Knowledge Base</h3>
                          <p className="text-sm text-muted-foreground">
                            Add static information the agent needs to know here. This information is automatically included in the prompt.
                          </p>
                        </div>
                      </div>
                      
                      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg mb-4">
                        <p className="text-sm text-blue-600 dark:text-blue-400">
                          💡 <strong>Tip:</strong> Enter information that the AI will provide to customers, such as prices, FAQs, product details, and company policies.
                        </p>
                      </div>

                      <textarea
                        value={knowledgeBase}
                        onChange={(e) => { setKnowledgeBase(e.target.value); setHasChanges(true); }}
                        placeholder={`## Pricing
- Residential electricity: $0.12/kWh
- Commercial electricity: $0.15/kWh
- Natural gas: $1.05/m³

## Promotions
- First 3 months 10% discount
- Online payment 5% discount
- 12-month installment option

## Frequently Asked Questions
Q: When are invoices issued?
A: On the 15th of each month.

Q: What are the payment channels?
A: Credit card, bank transfer, automatic payment order.

## Company Information
- Business hours: Weekdays 09:00-18:00
- Customer service: 1-800-XXX-XXXX`}
                        className="flex-1 min-h-[500px] w-full p-4 bg-muted/30 rounded-xl text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 border border-border leading-relaxed"
                      />
                    </div>
                  </div>
                )}

                {/* Web Sources Sub-tab */}
                {ragSubTab === 'sources' && (
                  <div className="p-6 space-y-4 flex-1 overflow-auto">
                    <div className="flex flex-col gap-4 h-full">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">Web Sources</h3>
                          <p className="text-sm text-muted-foreground">
                            Web sources the agent can search. Information is dynamically retrieved during calls.
                          </p>
                        </div>
                        <button
                          onClick={() => {
                            setWebSources([...webSources, { url: '', name: '', description: '' }]);
                            setHasChanges(true);
                          }}
                          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                        >
                          <Plus className="h-4 w-4" />
                          Add Source
                        </button>
                      </div>
                      
                      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                        <p className="text-sm text-amber-600 dark:text-amber-400">
                          🌐 <strong>Note:</strong> Web sources are sites that the agent dynamically queries using the &quot;search_web_source&quot; tool during calls. Use web sources instead of putting too much information in the prompt.
                        </p>
                      </div>

                      {webSources.length === 0 ? (
                        <div className="flex-1 flex items-center justify-center border-2 border-dashed border-border rounded-xl p-8">
                          <div className="text-center">
                            <p className="text-muted-foreground mb-2">No web sources added yet</p>
                            <button
                              onClick={() => {
                                setWebSources([{ url: '', name: '', description: '' }]);
                                setHasChanges(true);
                              }}
                              className="text-primary-500 hover:underline text-sm"
                            >
                              Add your first source
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {webSources.map((source, index) => (
                            <div key={index} className="p-4 bg-muted/30 rounded-xl border border-border space-y-3">
                              <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-muted-foreground">Source #{index + 1}</span>
                                <button
                                  onClick={() => {
                                    const newSources = webSources.filter((_, i) => i !== index);
                                    setWebSources(newSources);
                                    setHasChanges(true);
                                  }}
                                  className="p-1.5 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                              
                              <div className="space-y-2">
                                <label className="text-sm font-medium">URL <span className="text-red-500">*</span></label>
                                <input
                                  type="url"
                                  value={source.url}
                                  onChange={(e) => {
                                    const newSources = [...webSources];
                                    newSources[index].url = e.target.value;
                                    setWebSources(newSources);
                                    setHasChanges(true);
                                  }}
                                  placeholder="https://example.com/faq"
                                  className="w-full px-4 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                />
                              </div>
                              
                              <div className="space-y-2">
                                <label className="text-sm font-medium">Name</label>
                                <input
                                  type="text"
                                  value={source.name}
                                  onChange={(e) => {
                                    const newSources = [...webSources];
                                    newSources[index].name = e.target.value;
                                    setWebSources(newSources);
                                    setHasChanges(true);
                                  }}
                                  placeholder="FAQ Page"
                                  className="w-full px-4 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                />
                              </div>
                              
                              <div className="space-y-2">
                                <label className="text-sm font-medium">Description</label>
                                <textarea
                                  value={source.description}
                                  onChange={(e) => {
                                    const newSources = [...webSources];
                                    newSources[index].description = e.target.value;
                                    setWebSources(newSources);
                                    setHasChanges(true);
                                  }}
                                  placeholder="This source contains company FAQ information: prices, payment methods, contact info..."
                                  rows={2}
                                  className="w-full px-4 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Documents Sub-tab */}
                {ragSubTab === 'documents' && (
                  <div className="p-6 space-y-4 flex-1 overflow-auto">
                    <div className="flex flex-col gap-4 h-full">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-lg font-semibold">Documents (RAG)</h3>
                          <p className="text-sm text-muted-foreground">
                            Upload PDF, TXT, or DOCX files. The agent can search these documents for information during calls.
                          </p>
                        </div>
                        <label className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors cursor-pointer">
                          <Plus className="h-4 w-4" />
                          Upload File
                          <input
                            type="file"
                            accept=".pdf,.txt,.docx"
                            className="hidden"
                            disabled={isUploading}
                            onChange={async (e) => {
                              const file = e.target.files?.[0];
                              if (!file) return;
                              
                              setIsUploading(true);
                              try {
                                const formData = new FormData();
                                formData.append('file', file);
                                
                                const token = localStorage.getItem('access_token');
                                const response = await fetch(`${API_V1}/agents/${agentId}/documents/upload`, {
                                  method: 'POST',
                                  headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                                  body: formData,
                                });
                                
                                if (!response.ok) {
                                  const error = await response.json();
                                  throw new Error(error.detail || 'Failed to upload file');
                                }
                                
                                const newDoc = await response.json();
                                setDocuments([newDoc, ...documents]);
                                toast.success('File uploaded, processing...');
                              } catch (error) {
                                console.error('Upload error:', error);
                                toast.error(error instanceof Error ? error.message : 'Failed to upload file');
                              } finally {
                                setIsUploading(false);
                                e.target.value = '';
                              }
                            }}
                          />
                        </label>
                      </div>
                      
                      <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                        <p className="text-sm text-purple-600 dark:text-purple-400">
                          📚 <strong>RAG (Retrieval Augmented Generation):</strong> Uploaded documents are automatically processed and the agent accesses this information using the &quot;search_documents&quot; tool during calls. The most relevant information is found via semantic search.
                        </p>
                      </div>

                      {documents.length === 0 ? (
                        <div className="flex-1 flex items-center justify-center border-2 border-dashed border-border rounded-xl p-8 min-h-[300px]">
                          <div className="text-center">
                            <p className="text-muted-foreground mb-2">No documents uploaded yet</p>
                            <p className="text-xs text-muted-foreground">PDF, TXT, or DOCX files are supported (max 10 MB)</p>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {documents.map((doc) => (
                            <div key={doc.id} className="p-4 bg-muted/30 rounded-xl border border-border flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={cn(
                                  "w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold text-xs",
                                  doc.file_type === 'pdf' ? 'bg-red-500' :
                                  doc.file_type === 'docx' ? 'bg-blue-500' : 'bg-gray-500'
                                )}>
                                  {doc.file_type.toUpperCase()}
                                </div>
                                <div>
                                  <p className="font-medium">{doc.filename}</p>
                                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                                    {doc.status === 'ready' && (
                                      <>
                                        <span>•</span>
                                        <span>{doc.chunk_count} chunks</span>
                                        <span>•</span>
                                        <span>{doc.token_count.toLocaleString()} tokens</span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                {doc.status === 'pending' && (
                                  <span className="px-2 py-1 text-xs bg-yellow-500/20 text-yellow-600 rounded">Pending</span>
                                )}
                                {doc.status === 'processing' && (
                                  <span className="px-2 py-1 text-xs bg-blue-500/20 text-blue-600 rounded flex items-center gap-1">
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                    Processing
                                  </span>
                                )}
                                {doc.status === 'ready' && (
                                  <span className="px-2 py-1 text-xs bg-green-500/20 text-green-600 rounded">Ready</span>
                                )}
                                {doc.status === 'error' && (
                                  <span className="px-2 py-1 text-xs bg-red-500/20 text-red-600 rounded" title={doc.error_message}>Error</span>
                                )}
                                <button
                                  onClick={async () => {
                                    try {
                                      const response = await fetch(`${API_V1}/agents/${agentId}/documents/${doc.id}`, {
                                        method: 'DELETE',
                                      });
                                      if (!response.ok) throw new Error('Failed to delete');
                                      setDocuments(documents.filter(d => d.id !== doc.id));
                                      toast.success('Document deleted');
                                    } catch (error) {
                                      toast.error('Failed to delete document');
                                    }
                                  }}
                                  className="p-1.5 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Greeting Tab */}
            {activeTab === 'greeting' && (
              <div className="p-6 space-y-6">
                {/* First Speaker */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">First Speaker</label>
                    <Tooltip content="Who speaks first in the conversation">
                      <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                    </Tooltip>
                  </div>
                  <select
                    value={firstSpeaker}
                    onChange={(e) => { setFirstSpeaker(e.target.value as 'agent' | 'user'); setHasChanges(true); }}
                    className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="agent">Agent</option>
                    <option value="user">User</option>
                  </select>
                </div>

                {/* First Message */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">First Message / Greeting</label>
                    <Tooltip content="The first message the agent will say. Use {variables} for dynamic content.">
                      <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                    </Tooltip>
                  </div>
                  <textarea
                    value={greetingMessage}
                    onChange={(e) => { setGreetingMessage(e.target.value); setHasChanges(true); }}
                    placeholder="Hello {first_name}, I'm {agent_name}. How can I help you?"
                    rows={4}
                    className="w-full px-4 py-3 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                  />
                  
                  {/* Variable hints */}
                  <div className="p-3 bg-muted/20 rounded-lg border border-border/50">
                    <p className="text-xs font-medium text-muted-foreground mb-2">Available Variables:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        { var: '{customer_name}', desc: 'Full name' },
                        { var: '{first_name}', desc: 'First name' },
                        { var: '{company}', desc: 'Company' },
                        { var: '{amount}', desc: 'Amount' },
                        { var: '{due_date}', desc: 'Due date' },
                        { var: '{agent_name}', desc: 'Agent name' },
                        { var: '{date}', desc: 'Today' },
                        { var: '{day}', desc: 'Day of week' },
                      ].map((v) => (
                        <button
                          key={v.var}
                          onClick={() => {
                            setGreetingMessage(prev => prev + ' ' + v.var);
                            setHasChanges(true);
                          }}
                          className="px-2 py-1 text-xs bg-primary-500/10 text-primary-500 rounded hover:bg-primary-500/20 transition-colors"
                          title={v.desc}
                        >
                          {v.var}
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      💡 Custom columns uploaded from Excel can also be used as variables.
                    </p>
                  </div>
                </div>

                {/* Uninterruptible */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Uninterruptible</label>
                    <Tooltip content="If enabled, the user cannot interrupt the first message">
                      <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                    </Tooltip>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                    <span className="text-sm">{uninterruptible ? 'Enabled' : 'Disabled'}</span>
                    <button
                      onClick={() => { setUninterruptible(!uninterruptible); setHasChanges(true); }}
                      className={cn(
                        'w-12 h-6 rounded-full transition-colors relative',
                        uninterruptible ? 'bg-primary-500' : 'bg-muted'
                      )}
                    >
                      <span
                        className={cn(
                          'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                          uninterruptible ? 'translate-x-7' : 'translate-x-1'
                        )}
                      />
                    </button>
                  </div>
                </div>

                {/* First Message Delay */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">First Message Delay (s)</label>
                    <Tooltip content="Delay in seconds before the first message is spoken">
                      <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                    </Tooltip>
                  </div>
                  <input
                    type="number"
                    value={firstMessageDelay}
                    onChange={(e) => { setFirstMessageDelay(e.target.value); setHasChanges(true); }}
                    placeholder=""
                    className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            )}

            {/* Inactivity Messages Tab */}
            {activeTab === 'inactivity' && (
              <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">Inactivity Messages</h3>
                    <p className="text-sm text-muted-foreground">
                      Messages to play when the user is inactive for a specified duration.
                    </p>
                  </div>
                  <button
                    onClick={addInactivityMessage}
                    className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg text-sm font-medium transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    Add Message
                  </button>
                </div>

                {/* Messages */}
                <div className="space-y-4">
                  {inactivityMessages.map((msg, index) => (
                    <div key={msg.id} className="p-4 bg-muted/30 rounded-xl border border-border space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Message {index + 1}</span>
                        <button
                          onClick={() => removeInactivityMessage(msg.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-red-500 hover:bg-red-500/10 rounded-lg text-sm transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                          Remove
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        {/* Duration */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium">Duration (s)</label>
                          <input
                            type="number"
                            value={msg.duration}
                            onChange={(e) => updateInactivityMessage(msg.id, 'duration', parseInt(e.target.value) || 0)}
                            className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </div>

                        {/* End Behavior */}
                        <div className="space-y-2">
                          <label className="text-sm font-medium">End Behavior</label>
                          <select
                            value={msg.endBehavior}
                            onChange={(e) => updateInactivityMessage(msg.id, 'endBehavior', e.target.value)}
                            className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                          >
                            <option value="unspecified">Unspecified</option>
                            <option value="interruptible_hangup">Interruptible Hang Up</option>
                            <option value="uninterruptible_hangup">Uninterruptible Hang Up</option>
                          </select>
                        </div>
                      </div>

                      {/* Message */}
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Message</label>
                        <textarea
                          value={msg.message}
                          onChange={(e) => updateInactivityMessage(msg.id, 'message', e.target.value)}
                          placeholder="Example: Are you still there? Please let me know if you need any help."
                          rows={2}
                          className="w-full px-4 py-3 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Lead Capture Tab */}
            {activeTab === 'lead_capture' && (
              <div className="p-6 space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Lead Capture</h3>
                    <p className="text-sm text-muted-foreground">
                      Automatically create a lead record when the customer shows interest
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={leadCaptureEnabled}
                      onChange={(e) => { setLeadCaptureEnabled(e.target.checked); setHasChanges(true); }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-primary-500 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                  </label>
                </div>

                {leadCaptureEnabled && (
                  <div className="space-y-4">
                    {/* Triggers */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Triggers</label>
                      <p className="text-xs text-muted-foreground">In which situations should leads be captured?</p>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { id: 'interested', label: 'Showed Interest', desc: 'Phrases like "I\'m interested", "OK"' },
                          { id: 'callback', label: 'Requested Callback', desc: '"Call me back", "Let\'s talk later"' },
                          { id: 'purchase', label: 'Purchase Intent', desc: '"I want to buy", "Place an order"' },
                          { id: 'subscription', label: 'Subscription/Membership', desc: '"I want to subscribe"' },
                          { id: 'info_request', label: 'Information Request', desc: '"Send me info", "Can I get details?"' },
                          { id: 'address_shared', label: 'Shared Address', desc: 'Customer provided address information' },
                        ].map((trigger) => (
                          <label
                            key={trigger.id}
                            className={cn(
                              "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                              leadCaptureTriggers.includes(trigger.id)
                                ? "border-primary-500 bg-primary-500/10"
                                : "border-border hover:border-primary-500/50"
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={leadCaptureTriggers.includes(trigger.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setLeadCaptureTriggers([...leadCaptureTriggers, trigger.id]);
                                } else {
                                  setLeadCaptureTriggers(leadCaptureTriggers.filter(t => t !== trigger.id));
                                }
                                setHasChanges(true);
                              }}
                              className="mt-0.5"
                            />
                            <div>
                              <span className="text-sm font-medium">{trigger.label}</span>
                              <p className="text-xs text-muted-foreground">{trigger.desc}</p>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Default Priority */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Default Priority</label>
                      <select
                        value={leadCaptureDefaultPriority}
                        onChange={(e) => { setLeadCaptureDefaultPriority(parseInt(e.target.value)); setHasChanges(true); }}
                        className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value={1}>High (Follow up immediately)</option>
                        <option value={2}>Medium</option>
                        <option value={3}>Low</option>
                      </select>
                    </div>

                    {/* Options */}
                    <div className="space-y-3">
                      <label className="text-sm font-medium">Options</label>
                      <div className="space-y-2">
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={leadCaptureAutoPhone}
                            onChange={(e) => { setLeadCaptureAutoPhone(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Automatically save phone number</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={leadCaptureAutoAddress}
                            onChange={(e) => { setLeadCaptureAutoAddress(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Automatically save address</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={leadCaptureRequireConfirmation}
                            onChange={(e) => { setLeadCaptureRequireConfirmation(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Ask customer for confirmation ("Shall I save your information?")</span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Call Tags Tab */}
            {activeTab === 'call_tags' && (
              <div className="p-6 space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Call Tags</h3>
                    <p className="text-sm text-muted-foreground">
                      Automatically add tags based on call outcome
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={callTagsEnabled}
                      onChange={(e) => { setCallTagsEnabled(e.target.checked); setHasChanges(true); }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-primary-500 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                  </label>
                </div>

                {callTagsEnabled && (
                  <div className="space-y-4">
                    {/* Auto Tag Triggers */}
                    <div className="space-y-3">
                      <label className="text-sm font-medium">Auto Tagging</label>
                      <div className="space-y-2">
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={callTagsOnInterest}
                            onChange={(e) => { setCallTagsOnInterest(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Add "interested" tag when interest is shown</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={callTagsOnRejection}
                            onChange={(e) => { setCallTagsOnRejection(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Add "not_interested" tag when rejected</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={callTagsOnCallback}
                            onChange={(e) => { setCallTagsOnCallback(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Add "callback" tag when callback is requested</span>
                        </label>
                      </div>
                    </div>

                    {/* Default Tags */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Default Tags</label>
                      <p className="text-xs text-muted-foreground">Tags that will be automatically added to every call</p>
                      <div className="flex flex-wrap gap-2">
                        {['interested', 'not_interested', 'callback', 'hot_lead', 'cold_lead', 'do_not_call', 'wrong_number', 'voicemail', 'busy', 'complaint'].map((tag) => (
                          <label
                            key={tag}
                            className={cn(
                              "px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-colors border",
                              callTagsAutoTags.includes(tag)
                                ? "bg-primary-500 text-white border-primary-500"
                                : "bg-muted text-muted-foreground border-border hover:border-primary-500"
                            )}
                          >
                            <input
                              type="checkbox"
                              checked={callTagsAutoTags.includes(tag)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setCallTagsAutoTags([...callTagsAutoTags, tag]);
                                } else {
                                  setCallTagsAutoTags(callTagsAutoTags.filter(t => t !== tag));
                                }
                                setHasChanges(true);
                              }}
                              className="sr-only"
                            />
                            {tag.replace('_', ' ')}
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Callback Tab */}
            {activeTab === 'callback' && (
              <div className="p-6 space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Callback Scheduling</h3>
                    <p className="text-sm text-muted-foreground">
                      Schedule automatic callbacks when the customer is unavailable
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={callbackEnabled}
                      onChange={(e) => { setCallbackEnabled(e.target.checked); setHasChanges(true); }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-primary-500 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                  </label>
                </div>

                {callbackEnabled && (
                  <div className="space-y-4">
                    {/* Default Delay */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Default Callback Delay</label>
                      <select
                        value={callbackDefaultDelayHours}
                        onChange={(e) => { setCallbackDefaultDelayHours(parseInt(e.target.value)); setHasChanges(true); }}
                        className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value={1}>After 1 hour</option>
                        <option value={2}>After 2 hours</option>
                        <option value={4}>After 4 hours</option>
                        <option value={24}>After 1 day</option>
                        <option value={48}>After 2 days</option>
                        <option value={72}>After 3 days</option>
                        <option value={168}>After 1 week</option>
                      </select>
                    </div>

                    {/* Max Attempts */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Maximum Retry Attempts</label>
                      <input
                        type="number"
                        min={1}
                        max={10}
                        value={callbackMaxAttempts}
                        onChange={(e) => { setCallbackMaxAttempts(parseInt(e.target.value) || 3); setHasChanges(true); }}
                        className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                      <p className="text-xs text-muted-foreground">Maximum number of retry attempts if unreachable</p>
                    </div>

                    {/* Options */}
                    <div className="space-y-3">
                      <label className="text-sm font-medium">Options</label>
                      <div className="space-y-2">
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={callbackRespectBusinessHours}
                            onChange={(e) => { setCallbackRespectBusinessHours(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Respect business hours (no night calls)</span>
                        </label>
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={callbackAskPreferredTime}
                            onChange={(e) => { setCallbackAskPreferredTime(e.target.checked); setHasChanges(true); }}
                          />
                          <span className="text-sm">Ask customer for preferred time</span>
                        </label>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Survey Tab */}
            {activeTab === 'survey' && (
              <div className="p-6 space-y-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">Survey System</h3>
                    <p className="text-sm text-muted-foreground">
                      Collect survey responses from customers during calls
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={surveyEnabled}
                      onChange={(e) => { setSurveyEnabled(e.target.checked); setHasChanges(true); }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-primary-500 after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
                  </label>
                </div>

                {surveyEnabled && (
                  <div className="space-y-6">
                    {/* Survey Settings */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Completion Message</label>
                        <input
                          type="text"
                          value={surveyCompletionMessage}
                          onChange={(e) => { setSurveyCompletionMessage(e.target.value); setHasChanges(true); }}
                          placeholder="Thank you for participating in our survey!"
                          className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">Abort Message</label>
                        <input
                          type="text"
                          value={surveyAbortMessage}
                          onChange={(e) => { setSurveyAbortMessage(e.target.value); setHasChanges(true); }}
                          placeholder="Survey cancelled."
                          className="w-full px-4 py-2.5 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                        />
                      </div>
                    </div>

                    {/* Survey Options */}
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={surveyShowProgress}
                          onChange={(e) => { setSurveyShowProgress(e.target.checked); setHasChanges(true); }}
                        />
                        <span className="text-sm">Show progress (e.g.: question 2/5)</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={surveyAllowSkip}
                          onChange={(e) => { setSurveyAllowSkip(e.target.checked); setHasChanges(true); }}
                        />
                        <span className="text-sm">Allow skipping questions</span>
                      </label>
                    </div>

                    {/* Questions List */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">Survey Questions ({surveyQuestions.length})</h4>
                        <button
                          onClick={() => {
                            const newId = `q${surveyQuestions.length + 1}`;
                            const newQuestion: SurveyQuestion = {
                              id: newId,
                              type: 'yes_no',
                              text: '',
                              required: true,
                              next: null,
                            };
                            setSurveyQuestions([...surveyQuestions, newQuestion]);
                            setEditingQuestionId(newId);
                            setHasChanges(true);
                          }}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                        >
                          <Plus className="h-4 w-4" />
                          Add Question
                        </button>
                      </div>

                      {surveyQuestions.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground border-2 border-dashed border-border rounded-lg">
                          <p>No questions added yet.</p>
                          <p className="text-sm mt-1">Click the button above to add your first question.</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {surveyQuestions.map((question, index) => (
                            <div
                              key={question.id}
                              className={`border rounded-lg overflow-hidden ${editingQuestionId === question.id ? 'border-primary-500 ring-2 ring-primary-500/20' : 'border-border'}`}
                            >
                              {/* Question Header - Always visible */}
                              <div
                                className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/30"
                                onClick={() => setEditingQuestionId(editingQuestionId === question.id ? null : question.id)}
                              >
                                <div className="flex items-center gap-3">
                                  <span className="text-sm font-mono text-muted-foreground">{question.id}</span>
                                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                                    question.type === 'yes_no' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                    question.type === 'multiple_choice' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' :
                                    question.type === 'rating' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                    'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                  }`}>
                                    {question.type === 'yes_no' ? 'Yes/No' :
                                     question.type === 'multiple_choice' ? 'Multiple Choice' :
                                     question.type === 'rating' ? 'Rating' : 'Open Ended'}
                                  </span>
                                  <span className="text-sm truncate max-w-md">{question.text || '(No question text entered)'}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  {index === 0 && (
                                    <span className="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 rounded">Start</span>
                                  )}
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      const newQuestions = surveyQuestions.filter(q => q.id !== question.id);
                                      setSurveyQuestions(newQuestions);
                                      setHasChanges(true);
                                      if (editingQuestionId === question.id) setEditingQuestionId(null);
                                    }}
                                    className="p-1 text-muted-foreground hover:text-red-500 transition-colors"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                  <ChevronRight className={`h-4 w-4 text-muted-foreground transition-transform ${editingQuestionId === question.id ? 'rotate-90' : ''}`} />
                                </div>
                              </div>

                              {/* Question Editor - Expanded */}
                              {editingQuestionId === question.id && (
                                <div className="p-4 pt-0 space-y-4 border-t border-border bg-muted/10">
                                  {/* Question ID and Type */}
                                  <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                      <label className="text-sm font-medium">Question ID</label>
                                      <input
                                        type="text"
                                        value={question.id}
                                        onChange={(e) => {
                                          const newId = e.target.value.replace(/\s/g, '_');
                                          const updated = surveyQuestions.map(q => 
                                            q.id === question.id ? { ...q, id: newId } : q
                                          );
                                          setSurveyQuestions(updated);
                                          setEditingQuestionId(newId);
                                          setHasChanges(true);
                                        }}
                                        className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                                      />
                                    </div>
                                    <div className="space-y-2">
                                      <label className="text-sm font-medium">Question Type</label>
                                      <select
                                        value={question.type}
                                        onChange={(e) => {
                                          const updated = surveyQuestions.map(q => 
                                            q.id === question.id ? { ...q, type: e.target.value as SurveyQuestionType } : q
                                          );
                                          setSurveyQuestions(updated);
                                          setHasChanges(true);
                                        }}
                                        className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                      >
                                        <option value="yes_no">Yes / No</option>
                                        <option value="multiple_choice">Multiple Choice</option>
                                        <option value="rating">Rating (1-10)</option>
                                        <option value="open_ended">Open Ended</option>
                                      </select>
                                    </div>
                                  </div>

                                  {/* Question Text */}
                                  <div className="space-y-2">
                                    <label className="text-sm font-medium">Question Text</label>
                                    <textarea
                                      value={question.text}
                                      onChange={(e) => {
                                        const updated = surveyQuestions.map(q => 
                                          q.id === question.id ? { ...q, text: e.target.value } : q
                                        );
                                        setSurveyQuestions(updated);
                                        setHasChanges(true);
                                      }}
                                      placeholder="Enter question text..."
                                      rows={2}
                                      className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                    />
                                  </div>

                                  {/* Type-specific options */}
                                  {question.type === 'multiple_choice' && (
                                    <div className="space-y-2">
                                      <label className="text-sm font-medium">Options (one option per line)</label>
                                      <textarea
                                        value={(question.options || []).join('\n')}
                                        onChange={(e) => {
                                          const options = e.target.value.split('\n').filter(o => o.trim());
                                          const updated = surveyQuestions.map(q => 
                                            q.id === question.id ? { ...q, options } : q
                                          );
                                          setSurveyQuestions(updated);
                                          setHasChanges(true);
                                        }}
                                        placeholder="Option 1&#10;Option 2&#10;Option 3"
                                        rows={4}
                                        className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                                      />
                                      <label className="flex items-center gap-2 cursor-pointer">
                                        <input
                                          type="checkbox"
                                          checked={question.allow_multiple || false}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, allow_multiple: e.target.checked } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                        />
                                        <span className="text-sm">Allow multiple selections</span>
                                      </label>
                                    </div>
                                  )}

                                  {question.type === 'rating' && (
                                    <div className="grid grid-cols-4 gap-4">
                                      <div className="space-y-2">
                                        <label className="text-sm font-medium">Min Value</label>
                                        <input
                                          type="number"
                                          value={question.min_value ?? 1}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, min_value: parseInt(e.target.value) || 1 } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        />
                                      </div>
                                      <div className="space-y-2">
                                        <label className="text-sm font-medium">Max Value</label>
                                        <input
                                          type="number"
                                          value={question.max_value ?? 10}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, max_value: parseInt(e.target.value) || 10 } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        />
                                      </div>
                                      <div className="space-y-2">
                                        <label className="text-sm font-medium">Min Label</label>
                                        <input
                                          type="text"
                                          value={question.min_label || ''}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, min_label: e.target.value } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          placeholder="Very bad"
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        />
                                      </div>
                                      <div className="space-y-2">
                                        <label className="text-sm font-medium">Max Label</label>
                                        <input
                                          type="text"
                                          value={question.max_label || ''}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, max_label: e.target.value } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          placeholder="Excellent"
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        />
                                      </div>
                                    </div>
                                  )}

                                  {question.type === 'open_ended' && (
                                    <div className="grid grid-cols-2 gap-4">
                                      <div className="space-y-2">
                                        <label className="text-sm font-medium">Max Characters</label>
                                        <input
                                          type="number"
                                          value={question.max_length ?? 500}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, max_length: parseInt(e.target.value) || 500 } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        />
                                      </div>
                                      <div className="space-y-2">
                                        <label className="text-sm font-medium">Placeholder</label>
                                        <input
                                          type="text"
                                          value={question.placeholder || ''}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, placeholder: e.target.value } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          placeholder="Share your thoughts..."
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        />
                                      </div>
                                    </div>
                                  )}

                                  {/* Branching */}
                                  <div className="border-t border-border pt-4 space-y-3">
                                    <label className="text-sm font-medium flex items-center gap-2">
                                      <GitBranch className="h-4 w-4" />
                                      Conditional Branching
                                    </label>
                                    
                                    {question.type === 'yes_no' ? (
                                      <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                          <label className="text-sm text-muted-foreground">On Yes answer →</label>
                                          <select
                                            value={question.next_on_yes || ''}
                                            onChange={(e) => {
                                              const updated = surveyQuestions.map(q => 
                                                q.id === question.id ? { ...q, next_on_yes: e.target.value || null } : q
                                              );
                                              setSurveyQuestions(updated);
                                              setHasChanges(true);
                                            }}
                                            className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                          >
                                            <option value="">End survey</option>
                                            {surveyQuestions.filter(q => q.id !== question.id).map(q => (
                                              <option key={q.id} value={q.id}>{q.id}: {q.text.substring(0, 40)}...</option>
                                            ))}
                                          </select>
                                        </div>
                                        <div className="space-y-2">
                                          <label className="text-sm text-muted-foreground">On No answer →</label>
                                          <select
                                            value={question.next_on_no || ''}
                                            onChange={(e) => {
                                              const updated = surveyQuestions.map(q => 
                                                q.id === question.id ? { ...q, next_on_no: e.target.value || null } : q
                                              );
                                              setSurveyQuestions(updated);
                                              setHasChanges(true);
                                            }}
                                            className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                          >
                                            <option value="">End survey</option>
                                            {surveyQuestions.filter(q => q.id !== question.id).map(q => (
                                              <option key={q.id} value={q.id}>{q.id}: {q.text.substring(0, 40)}...</option>
                                            ))}
                                          </select>
                                        </div>
                                      </div>
                                    ) : (
                                      <div className="space-y-2">
                                        <label className="text-sm text-muted-foreground">Next question →</label>
                                        <select
                                          value={question.next || ''}
                                          onChange={(e) => {
                                            const updated = surveyQuestions.map(q => 
                                              q.id === question.id ? { ...q, next: e.target.value || null } : q
                                            );
                                            setSurveyQuestions(updated);
                                            setHasChanges(true);
                                          }}
                                          className="w-full px-3 py-2 bg-background rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                                        >
                                          <option value="">End survey</option>
                                          {surveyQuestions.filter(q => q.id !== question.id).map(q => (
                                            <option key={q.id} value={q.id}>{q.id}: {q.text.substring(0, 40)}...</option>
                                          ))}
                                        </select>
                                      </div>
                                    )}
                                  </div>

                                  {/* Required */}
                                  <label className="flex items-center gap-2 cursor-pointer">
                                    <input
                                      type="checkbox"
                                      checked={question.required}
                                      onChange={(e) => {
                                        const updated = surveyQuestions.map(q => 
                                          q.id === question.id ? { ...q, required: e.target.checked } : q
                                        );
                                        setSurveyQuestions(updated);
                                        setHasChanges(true);
                                      }}
                                    />
                                    <span className="text-sm">Required question</span>
                                  </label>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Settings Tab */}
            {activeTab === 'settings' && (
              <div className="p-6 space-y-6">
                {/* Provider Selection */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">AI Provider</label>
                  <div className="grid grid-cols-3 gap-3">
                    <button
                      onClick={() => {
                        setSelectedProvider('openai');
                        setSelectedModel('gpt-realtime-mini');
                        setSelectedVoice('alloy');
                        setVoiceGenderFilter('all');
                        setHasChanges(true);
                      }}
                      className={cn(
                        'p-3 rounded-lg border text-left transition-all',
                        selectedProvider === 'openai'
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <p className="font-medium text-sm">OpenAI Realtime</p>
                      <p className="text-xs text-muted-foreground">GPT-4o via Asterisk, token-based pricing</p>
                    </button>
                    <button
                      onClick={() => {
                        setSelectedProvider('ultravox');
                        setSelectedModel('ultravox-v0.7');
                        setSelectedVoice('Mark');
                        setVoiceGenderFilter('all');
                        setHasChanges(true);
                      }}
                      className={cn(
                        'p-3 rounded-lg border text-left transition-all',
                        selectedProvider === 'ultravox'
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <p className="font-medium text-sm">Ultravox</p>
                      <p className="text-xs text-muted-foreground">Native SIP, $0.05/min flat rate</p>
                    </button>
                    <button
                      onClick={() => {
                        setSelectedProvider('pipeline');
                        setSelectedModel('pipeline-qwen-7b');
                        setSelectedVoice('en_US-amy-medium');
                        setVoiceGenderFilter('all');
                        setHasChanges(true);
                      }}
                      className={cn(
                        'p-3 rounded-lg border text-left transition-all',
                        selectedProvider === 'pipeline'
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <p className="font-medium text-sm">Pipeline (Local)</p>
                      <p className="text-xs text-muted-foreground">Local STT + LLM + TTS, free</p>
                    </button>
                  </div>
                </div>

                {/* Basic Settings - 2 Column Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Model Selection */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Model</label>
                    <select
                      value={selectedModel}
                      onChange={(e) => { setSelectedModel(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      {selectedProvider === 'openai' ? (
                        <>
                          <option value="gpt-realtime-mini">gpt-realtime-mini ($10/$20 per 1M audio tokens)</option>
                          <option value="gpt-realtime">gpt-realtime ($32/$64 per 1M audio tokens)</option>
                        </>
                      ) : selectedProvider === 'pipeline' ? (
                        <>
                          <option value="pipeline-qwen-7b">Qwen 2.5 7B (fast, multilingual)</option>
                          <option value="pipeline-llama-8b">Llama 3.1 8B (balanced)</option>
                          <option value="pipeline-mistral-7b">Mistral 7B (efficient)</option>
                        </>
                      ) : (
                        <>
                          <option value="ultravox-v0.7">Ultravox v0.7 (latest, recommended)</option>
                          <option value="ultravox-v0.6">Ultravox v0.6</option>
                          <option value="ultravox-v0.6-gemma3-27b">Ultravox v0.6 gemma3-27b</option>
                          <option value="ultravox-v0.6-llama3.3-70b">Ultravox v0.6 llama3.3-70b</option>
                        </>
                      )}
                    </select>
                    <p className="text-xs text-muted-foreground">
                      {selectedProvider === 'openai'
                        ? 'Mini model is more cost-effective for most use cases.'
                        : selectedProvider === 'pipeline'
                        ? 'Local LLM via Ollama. Free, runs on your server.'
                        : 'Ultravox v0.7 is the latest model with best quality.'}
                    </p>
                  </div>

                  {/* Voice Selection */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Voice</label>
                      <div className="flex gap-1 bg-muted/30 rounded-lg p-0.5">
                        {[
                          { key: 'all' as const, label: 'All' },
                          { key: 'female' as const, label: '♀ Female' },
                          { key: 'male' as const, label: '♂ Male' },
                        ].map((f) => (
                          <button
                            key={f.key}
                            type="button"
                            onClick={() => setVoiceGenderFilter(f.key)}
                            className={cn(
                              'px-2 py-0.5 text-xs rounded-md transition-all',
                              voiceGenderFilter === f.key
                                ? 'bg-primary-500 text-white shadow-sm'
                                : 'text-muted-foreground hover:text-foreground'
                            )}
                          >
                            {f.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <select
                      value={selectedVoice}
                      onChange={(e) => { setSelectedVoice(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      {voices.map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.gender === 'male' ? '♂' : '♀'} {voice.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Language */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Language</label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => { setSelectedLanguage(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="tr">🇹🇷 Türkçe</option>
                      <option value="en">🇺🇸 English</option>
                      <option value="de">🇩🇪 Deutsch</option>
                      <option value="fr">🇫🇷 Français</option>
                      <option value="es">🇪🇸 Español</option>
                    </select>
                  </div>

                  {/* Timezone */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Timezone</label>
                    <select
                      value={selectedTimezone}
                      onChange={(e) => { setSelectedTimezone(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <optgroup label="Türkiye">
                        <option value="Europe/Istanbul">🇹🇷 İstanbul (UTC+3)</option>
                      </optgroup>
                      <optgroup label="Avrupa">
                        <option value="Europe/London">🇬🇧 Londra (UTC+0/+1)</option>
                        <option value="Europe/Berlin">🇩🇪 Berlin (UTC+1/+2)</option>
                        <option value="Europe/Paris">🇫🇷 Paris (UTC+1/+2)</option>
                        <option value="Europe/Madrid">🇪🇸 Madrid (UTC+1/+2)</option>
                        <option value="Europe/Rome">🇮🇹 Roma (UTC+1/+2)</option>
                        <option value="Europe/Amsterdam">🇳🇱 Amsterdam (UTC+1/+2)</option>
                        <option value="Europe/Brussels">🇧🇪 Brüksel (UTC+1/+2)</option>
                        <option value="Europe/Vienna">🇦🇹 Viyana (UTC+1/+2)</option>
                        <option value="Europe/Zurich">🇨🇭 Zürih (UTC+1/+2)</option>
                        <option value="Europe/Athens">🇬🇷 Atina (UTC+2/+3)</option>
                        <option value="Europe/Bucharest">🇷🇴 Bükreş (UTC+2/+3)</option>
                        <option value="Europe/Helsinki">🇫🇮 Helsinki (UTC+2/+3)</option>
                        <option value="Europe/Moscow">🇷🇺 Moskova (UTC+3)</option>
                      </optgroup>
                      <optgroup label="Amerika">
                        <option value="America/New_York">🇺🇸 New York (UTC-5/-4)</option>
                        <option value="America/Chicago">🇺🇸 Chicago (UTC-6/-5)</option>
                        <option value="America/Denver">🇺🇸 Denver (UTC-7/-6)</option>
                        <option value="America/Los_Angeles">🇺🇸 Los Angeles (UTC-8/-7)</option>
                        <option value="America/Toronto">🇨🇦 Toronto (UTC-5/-4)</option>
                        <option value="America/Sao_Paulo">🇧🇷 São Paulo (UTC-3)</option>
                        <option value="America/Mexico_City">🇲🇽 Mexico City (UTC-6/-5)</option>
                        <option value="America/Argentina/Buenos_Aires">🇦🇷 Buenos Aires (UTC-3)</option>
                      </optgroup>
                      <optgroup label="Asya / Pasifik">
                        <option value="Asia/Dubai">🇦🇪 Dubai (UTC+4)</option>
                        <option value="Asia/Riyadh">🇸🇦 Riyad (UTC+3)</option>
                        <option value="Asia/Tehran">🇮🇷 Tahran (UTC+3:30)</option>
                        <option value="Asia/Karachi">🇵🇰 Karaçi (UTC+5)</option>
                        <option value="Asia/Kolkata">🇮🇳 Mumbai (UTC+5:30)</option>
                        <option value="Asia/Bangkok">🇹🇭 Bangkok (UTC+7)</option>
                        <option value="Asia/Shanghai">🇨🇳 Şangay (UTC+8)</option>
                        <option value="Asia/Tokyo">🇯🇵 Tokyo (UTC+9)</option>
                        <option value="Asia/Seoul">🇰🇷 Seul (UTC+9)</option>
                        <option value="Australia/Sydney">🇦🇺 Sidney (UTC+10/+11)</option>
                        <option value="Pacific/Auckland">🇳🇿 Auckland (UTC+12/+13)</option>
                      </optgroup>
                      <optgroup label="Afrika">
                        <option value="Africa/Cairo">🇪🇬 Kahire (UTC+2)</option>
                        <option value="Africa/Johannesburg">🇿🇦 Johannesburg (UTC+2)</option>
                        <option value="Africa/Lagos">🇳🇬 Lagos (UTC+1)</option>
                        <option value="Africa/Casablanca">🇲🇦 Kazablanka (UTC+0/+1)</option>
                      </optgroup>
                    </select>
                  </div>

                  {/* Max Call Duration */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Max Call Duration (seconds)</label>
                    <input
                      type="number"
                      value={maxDuration}
                      onChange={(e) => { setMaxDuration(parseInt(e.target.value) || 300); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                {/* Toggle Switches - 2 Column Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Record Calls */}
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                    <div>
                      <p className="text-sm font-medium">Record Calls</p>
                      <p className="text-xs text-muted-foreground">Save audio recordings of all calls</p>
                    </div>
                    <button
                      onClick={() => { setRecordCalls(!recordCalls); setHasChanges(true); }}
                      className={cn(
                        'w-12 h-6 rounded-full transition-colors relative flex-shrink-0',
                        recordCalls ? 'bg-primary-500' : 'bg-muted'
                      )}
                    >
                      <span className={cn(
                        'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                        recordCalls ? 'translate-x-7' : 'translate-x-1'
                      )} />
                    </button>
                  </div>

                  {/* Auto Transcribe */}
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                    <div>
                      <p className="text-sm font-medium">Auto Transcribe</p>
                      <p className="text-xs text-muted-foreground">Automatically generate transcripts</p>
                    </div>
                    <button
                      onClick={() => { setAutoTranscribe(!autoTranscribe); setHasChanges(true); }}
                      className={cn(
                        'w-12 h-6 rounded-full transition-colors relative flex-shrink-0',
                        autoTranscribe ? 'bg-primary-500' : 'bg-muted'
                      )}
                    >
                      <span className={cn(
                        'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                        autoTranscribe ? 'translate-x-7' : 'translate-x-1'
                      )} />
                    </button>
                  </div>
                </div>

                {/* Divider */}
                <div className="border-t border-border pt-6 mt-6">
                  <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                    ⚙️ Advanced Settings
                  </h3>
                </div>

                {/* Advanced Settings - 3 Column Grid */}
                <div className="grid grid-cols-3 gap-4">
                  {/* Temperature */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Temperature</label>
                      <span className="text-sm text-muted-foreground">{temperature}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => { setTemperature(parseFloat(e.target.value)); setHasChanges(true); }}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">Controls randomness: 0 = deterministic, 1 = creative</p>
                  </div>

                  {/* Speech Speed */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">Speech Speed</label>
                      <span className="text-sm text-muted-foreground">{speechSpeed}x</span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="2"
                      step="0.1"
                      value={speechSpeed}
                      onChange={(e) => { setSpeechSpeed(parseFloat(e.target.value)); setHasChanges(true); }}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">Voice speed: 0.5 = slow, 1.0 = normal, 2.0 = fast</p>
                  </div>

                  {/* Turn Detection */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Turn Detection</label>
                    <select
                      value={turnDetection}
                      onChange={(e) => { setTurnDetection(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="server_vad">Server VAD (Voice Activity Detection)</option>
                      <option value="semantic_vad">Semantic VAD (AI-based)</option>
                      <option value="disabled">Disabled (Manual control)</option>
                    </select>
                    <p className="text-xs text-muted-foreground">How the system detects when user stops speaking</p>
                  </div>

                  {/* VAD Threshold */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">VAD Threshold</label>
                      <span className="text-sm text-muted-foreground">{vadThreshold}</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={vadThreshold}
                      onChange={(e) => { setVadThreshold(parseFloat(e.target.value)); setHasChanges(true); }}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">Higher = less sensitive to background noise</p>
                  </div>

                  {/* User Transcript Model */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">User Transcript Model</label>
                    <select
                      value={transcriptModel}
                      onChange={(e) => { setTranscriptModel(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="gpt-4o-transcribe">gpt-4o-transcribe</option>
                      <option value="whisper-1">whisper-1</option>
                    </select>
                    <p className="text-xs text-muted-foreground">Model for user speech transcription</p>
                  </div>

                  {/* Silence Timeout */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Silence Timeout (seconds)</label>
                    <input
                      type="number"
                      value={silenceTimeout}
                      onChange={(e) => { setSilenceTimeout(parseInt(e.target.value) || 10); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>

                {/* Semantic VAD Eagerness - only show if semantic_vad selected */}
                {turnDetection === 'semantic_vad' && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">VAD Eagerness</label>
                    <select
                      value={vadEagerness}
                      onChange={(e) => { setVadEagerness(e.target.value); setHasChanges(true); }}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    >
                      <option value="auto">Auto</option>
                      <option value="low">Low (wait longer)</option>
                      <option value="medium">Medium</option>
                      <option value="high">High (respond quickly)</option>
                    </select>
                    <p className="text-xs text-muted-foreground">How eager the AI is to take a turn</p>
                  </div>
                )}

                {/* More Advanced Settings - 2 Column Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Silence Duration */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Silence Duration (ms)</label>
                    <input
                      type="number"
                      value={silenceDurationMs}
                      onChange={(e) => { setSilenceDurationMs(parseInt(e.target.value) || 800); setHasChanges(true); }}
                      min={100}
                      max={5000}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-xs text-muted-foreground">How long to wait after user stops speaking (default: 800ms)</p>
                  </div>

                  {/* Prefix Padding */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Prefix Padding (ms)</label>
                    <input
                      type="number"
                      value={prefixPaddingMs}
                      onChange={(e) => { setPrefixPaddingMs(parseInt(e.target.value) || 500); setHasChanges(true); }}
                      min={100}
                      max={2000}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-xs text-muted-foreground">Audio padding before speech starts (default: 500ms)</p>
                  </div>

                  {/* Idle Timeout */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Idle Timeout (ms)</label>
                    <input
                      type="number"
                      value={idleTimeoutMs ?? ''}
                      onChange={(e) => { 
                        const val = e.target.value;
                        setIdleTimeoutMs(val === '' ? null : parseInt(val) || null); 
                        setHasChanges(true); 
                      }}
                      min={0}
                      max={60000}
                      placeholder="No timeout"
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-xs text-muted-foreground">Auto-close connection after inactivity (leave empty for no timeout)</p>
                  </div>

                  {/* Max Output Tokens */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Max Output Tokens</label>
                    <input
                      type="number"
                      value={maxOutputTokens}
                      onChange={(e) => { setMaxOutputTokens(parseInt(e.target.value) || 500); setHasChanges(true); }}
                      min={0}
                      max={4096}
                      className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-xs text-muted-foreground">Maximum response length (0 = infinite)</p>
                  </div>
                </div>

                {/* Advanced Toggles - 3 Column Grid */}
                <div className="grid grid-cols-3 gap-4">
                  {/* Interrupt Response Toggle */}
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                    <div>
                      <p className="text-sm font-medium">Allow Interruption</p>
                      <p className="text-xs text-muted-foreground">User can interrupt the AI</p>
                    </div>
                    <button
                      onClick={() => { setInterruptResponse(!interruptResponse); setHasChanges(true); }}
                      className={cn(
                        'w-12 h-6 rounded-full transition-colors relative flex-shrink-0',
                        interruptResponse ? 'bg-primary-500' : 'bg-muted'
                      )}
                    >
                      <span className={cn(
                        'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                        interruptResponse ? 'translate-x-7' : 'translate-x-1'
                      )} />
                    </button>
                  </div>

                  {/* Create Response Toggle */}
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                    <div>
                      <p className="text-sm font-medium">Auto Create Response</p>
                      <p className="text-xs text-muted-foreground">Auto respond when user stops</p>
                    </div>
                    <button
                      onClick={() => { setCreateResponse(!createResponse); setHasChanges(true); }}
                      className={cn(
                        'w-12 h-6 rounded-full transition-colors relative flex-shrink-0',
                        createResponse ? 'bg-primary-500' : 'bg-muted'
                      )}
                    >
                      <span className={cn(
                        'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                        createResponse ? 'translate-x-7' : 'translate-x-1'
                      )} />
                    </button>
                  </div>

                  {/* Noise Reduction Toggle */}
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                    <div>
                      <p className="text-sm font-medium">Noise Reduction</p>
                      <p className="text-xs text-muted-foreground">Filter background noise</p>
                    </div>
                    <button
                      onClick={() => { setNoiseReduction(!noiseReduction); setHasChanges(true); }}
                      className={cn(
                        'w-12 h-6 rounded-full transition-colors relative flex-shrink-0',
                        noiseReduction ? 'bg-primary-500' : 'bg-muted'
                      )}
                    >
                      <span className={cn(
                        'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                        noiseReduction ? 'translate-x-7' : 'translate-x-1'
                      )} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Console Tab */}
            {activeTab === 'console' && (
              <div className="h-full">
                <LiveConsole
                  agentId={agentId}
                  onClose={() => setActiveTab('prompt')}
                  className="h-full"
                />
              </div>
            )}
          </div>

          {/* Footer - Agent ID */}
          <div className="px-4 py-2 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="font-mono">{agentId.substring(0, 8)}...</span>
              <button 
                onClick={() => {
                  navigator.clipboard.writeText(agentId);
                  toast.success('Agent ID copied');
                }}
                className="hover:text-foreground transition-colors"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
            <span>last saved: 5 hours ago</span>
          </div>
        </div>
      </div>

      {/* AI Prompt Maker Modal */}
      <PromptMakerModal
        isOpen={isPromptMakerOpen}
        onClose={() => setIsPromptMakerOpen(false)}
        onGenerate={(generatedPrompt) => {
          // Set the unified prompt directly
          setPrompt(generatedPrompt);
          setHasChanges(true);
        }}
        existingPrompt={prompt}
      />
    </div>
  );
}
