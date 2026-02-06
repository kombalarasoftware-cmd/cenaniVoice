'use client';

import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { toast } from 'sonner';
import {
  ChevronLeft,
  Save,
  Play,
  Mic,
  MessageSquare,
  Plus,
  Trash2,
  ChevronDown,
  Volume2,
  Settings2,
  Info,
  Copy,
  Sparkles,
  X,
  Loader2,
  Wand2,
} from 'lucide-react';
import Link from 'next/link';

// ============================================
// Types
// ============================================
type EditorTab = 'prompt' | 'greeting' | 'inactivity' | 'settings';
type TestMode = 'voice' | 'text';
type EndBehavior = 'unspecified' | 'interruptible_hangup' | 'uninterruptible_hangup';

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
    { id: '', label: 'Seç...' },
    { id: 'sales', label: '🛒 Satış Temsilcisi' },
    { id: 'appointment', label: '📅 Randevu Asistanı' },
    { id: 'support', label: '🎧 Müşteri Destek' },
    { id: 'collection', label: '💰 Tahsilat' },
    { id: 'survey', label: '📋 Anket' },
  ];

  const tones = [
    { id: 'professional', label: 'Profesyonel' },
    { id: 'friendly', label: 'Samimi' },
    { id: 'formal', label: 'Resmi' },
    { id: 'casual', label: 'Günlük' },
  ];

  const quickSuggestions = [
    'Güneş enerjisi sistemleri satışı yapan bir temsilci, randevu alsın',
    'Borç hatırlatma yapan nazik ama kararlı bir temsilci',
    'Müşteri şikayetlerini dinleyen ve çözüm üreten destek temsilcisi',
    'Anket yapan kısa ve öz konuşan bir temsilci',
  ];

  const handleGenerate = async () => {
    if (!description.trim()) {
      setError('Lütfen ne tür bir agent istediğinizi açıklayın');
      return;
    }

    setIsGenerating(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/prompt-generator/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          agent_type: agentType || undefined,
          tone,
          existing_prompt: existingPrompt || undefined,
          language: 'tr',
        }),
      });

      if (!response.ok) {
        throw new Error('Prompt oluşturulamadı');
      }

      const data = await response.json();
      setGeneratedPrompt(data.prompt);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bir hata oluştu');
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
                Ne istediğinizi yazın, AI profesyonel bir prompt oluştursun
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
                <label className="text-sm font-medium">Agent&apos;ınızı tanımlayın</label>
                <textarea
                  value={description}
                  onChange={(e) => { setDescription(e.target.value); setError(''); }}
                  placeholder="Örn: Güneş enerjisi sistemleri satışı yapan bir firma için resepsiyon görevlisi. Müşterilerden gelen kısa taleplere hızlı, cana yakın ve yardımsever cevap versin."
                  rows={4}
                  className="w-full px-4 py-3 bg-muted/30 rounded-xl text-sm border border-border focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
                />
                {error && (
                  <p className="text-sm text-red-500">{error}</p>
                )}
              </div>

              {/* Quick Suggestions */}
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground uppercase tracking-wider">Hızlı Öneriler</label>
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
                  <label className="text-sm font-medium">Agent Tipi (opsiyonel)</label>
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
                  <label className="text-sm font-medium">Ton</label>
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
                    💡 Mevcut prompt&apos;unuz iyileştirilecek
                  </p>
                </div>
              )}
            </>
          ) : (
            /* Generated Prompt Preview */
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                <Wand2 className="h-4 w-4" />
                <span>Prompt oluşturuldu!</span>
              </div>
              <div className="relative">
                <textarea
                  value={generatedPrompt}
                  onChange={(e) => setGeneratedPrompt(e.target.value)}
                  rows={15}
                  className="w-full px-4 py-3 bg-muted/30 rounded-xl text-sm border border-border focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none font-mono"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  İsterseniz düzenleyebilirsiniz
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
                İptal
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
                    Oluşturuluyor...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Prompt Oluştur
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
                ← Geri Dön
              </button>
              <button
                onClick={handleApply}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-sm font-medium transition-colors shadow-lg shadow-emerald-500/25"
              >
                <Wand2 className="h-4 w-4" />
                Prompt&apos;u Uygula
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Test Call Modal Component
// ============================================
interface TestCallModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
}

function TestCallModal({ isOpen, onClose, agentId }: TestCallModalProps) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [isCalling, setIsCalling] = useState(false);

  if (!isOpen) return null;

  const handleTestCall = async () => {
    if (!phoneNumber.trim()) {
      toast.error('Lütfen telefon numarası girin');
      return;
    }

    setIsCalling(true);
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch('http://localhost:8000/api/v1/calls/outbound', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          phone_number: phoneNumber,
          agent_id: agentId,
          customer_name: customerName || undefined,
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast.success(`Arama başlatıldı: ${result.message}`);
        onClose();
        setPhoneNumber('');
        setCustomerName('');
      } else {
        toast.error(`Arama başlatılamadı: ${result.message}`);
      }
    } catch (error) {
      console.error('Test call error:', error);
      toast.error('Arama başlatılırken hata oluştu');
    } finally {
      setIsCalling(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-background rounded-2xl shadow-2xl max-w-md w-full border border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Play className="h-5 w-5 text-emerald-500" />
            <h2 className="text-lg font-semibold">Test Outbound Call</h2>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Telefon Numarası <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+90 555 123 4567 veya 905551234567"
              className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="text-xs text-muted-foreground">
              + işareti ile veya 90 ile başlayabilir
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              Müşteri İsmi (Opsiyonel)
            </label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder="örn: Ahmet Yılmaz"
              className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="text-xs text-muted-foreground">
              İsim yazarsanız agent müşteriye ismiyle hitap edecek
            </p>
          </div>

          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-600 dark:text-blue-400">
              💡 Test aramayı agent&apos;ınız gerçek bir aramayı simüle edecek
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
          <button
            onClick={onClose}
            disabled={isCalling}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            İptal
          </button>
          <button
            onClick={handleTestCall}
            disabled={isCalling || !phoneNumber.trim()}
            className={cn(
              'flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all',
              isCalling || !phoneNumber.trim()
                ? 'bg-muted text-muted-foreground cursor-not-allowed'
                : 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-lg shadow-emerald-500/25'
            )}
          >
            {isCalling ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Aranıyor...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Aramayı Başlat
              </>
            )}
          </button>
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
// Test Panel Component
// ============================================
function TestPanel() {
  const params = useParams();
  const agentId = params.id as string;
  const [testMode, setTestMode] = useState<TestMode>('text');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isAIThinking, setIsAIThinking] = useState(false);
  const [isTestCallModalOpen, setIsTestCallModalOpen] = useState(false);

  const sendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsAIThinking(true);

    setTimeout(() => {
      setIsAIThinking(false);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Bu bir test yanıtıdır. Gerçek entegrasyonda OpenAI Realtime API kullanılacaktır.',
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 1500);
  };

  const handleSuggestionSelect = (text: string) => {
    setInputValue(text);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          <span className="font-medium">New Chat</span>
        </div>
        <button 
          onClick={() => setIsTestCallModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Play className="h-4 w-4" />
          Test Agent
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            Start a conversation to test your agent
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={cn(
                  'max-w-[80%] px-4 py-2.5 rounded-2xl text-sm',
                  message.role === 'user'
                    ? 'bg-primary-500 text-white'
                    : 'bg-muted'
                )}
              >
                {message.content}
              </div>
            </div>
          ))
        )}
        {isAIThinking && (
          <div className="flex justify-start">
            <div className="bg-muted px-4 py-2.5 rounded-2xl">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Suggestions */}
      <div className="px-4 pb-2">
        <PromptSuggestions onSelect={handleSuggestionSelect} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2.5 bg-muted rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          
          {/* Mode Toggle */}
          <div className="flex items-center bg-muted rounded-xl p-1">
            <button
              onClick={() => setTestMode('voice')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                testMode === 'voice' ? 'bg-background shadow-sm' : 'text-muted-foreground'
              )}
            >
              <Mic className="h-4 w-4" />
              Voice
            </button>
            <button
              onClick={() => setTestMode('text')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                testMode === 'text' ? 'bg-background shadow-sm' : 'text-muted-foreground'
              )}
            >
              <MessageSquare className="h-4 w-4" />
              Text
            </button>
          </div>

          <span className="text-xs text-muted-foreground whitespace-nowrap">↵ Enter to Submit</span>
        </div>
      </div>

      {/* Test Call Modal */}
      <TestCallModal 
        isOpen={isTestCallModalOpen}
        onClose={() => setIsTestCallModalOpen(false)}
        agentId={agentId}
      />
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
  const [hasChanges, setHasChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [agentName, setAgentName] = useState('');
  const [isPromptMakerOpen, setIsPromptMakerOpen] = useState(false);
  const [isTestCallModalOpen, setIsTestCallModalOpen] = useState(false);
  
  // Prompt state
  const [prompt, setPrompt] = useState('');

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
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [selectedModel, setSelectedModel] = useState('gpt-realtime-mini');
  const [selectedLanguage, setSelectedLanguage] = useState('tr');
  const [maxDuration, setMaxDuration] = useState(300);
  const [silenceTimeout, setSilenceTimeout] = useState(10);
  const [recordCalls, setRecordCalls] = useState(true);
  const [autoTranscribe, setAutoTranscribe] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

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

        const response = await fetch(`http://localhost:8000/api/v1/agents/${agentId}`, {
          headers,
        });
        
        if (!response.ok) {
          throw new Error('Agent yüklenemedi');
        }
        
        const data = await response.json();
        setAgentName(data.name || '');
        setPrompt(data.prompt_role || '');
        setGreetingMessage(data.greeting_message || '');
        setFirstSpeaker(data.first_speaker || 'agent');
        setUninterruptible(data.greeting_uninterruptible ?? false);
        setFirstMessageDelay(data.first_message_delay ? data.first_message_delay.toString() : '');
        setSelectedVoice(data.voice || 'alloy');
        setSelectedModel(data.model_type || 'gpt-realtime-mini');
        setSelectedLanguage(data.language || 'tr');
        setMaxDuration(data.max_duration ?? 300);
        setSilenceTimeout(data.silence_timeout ?? 10);
        setRecordCalls(data.record_calls ?? true);
        setAutoTranscribe(data.auto_transcribe ?? true);
        
        // Load inactivity messages
        if (data.inactivity_messages && Array.isArray(data.inactivity_messages)) {
          setInactivityMessages(data.inactivity_messages.map((msg: any, index: number) => ({
            id: (index + 1).toString(),
            duration: msg.duration || 30,
            message: msg.message || '',
            endBehavior: msg.end_behavior || 'unspecified',
          })));
        }
      } catch (error) {
        console.error('Agent fetch error:', error);
        toast.error('Agent yüklenirken hata oluştu');
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
    { id: 'greeting' as EditorTab, label: 'Greeting' },
    { id: 'inactivity' as EditorTab, label: 'Inactivity Messages' },
    { id: 'settings' as EditorTab, label: 'Settings' },
  ];

  const voices = [
    { id: 'alloy', name: 'Alloy' },
    { id: 'echo', name: 'Echo' },
    { id: 'fable', name: 'Fable' },
    { id: 'onyx', name: 'Onyx' },
    { id: 'nova', name: 'Nova' },
    { id: 'shimmer', name: 'Shimmer' },
  ];

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

      const response = await fetch(`http://localhost:8000/api/v1/agents/${agentId}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          name: agentName,
          prompt: {
            role: prompt,
            personality: '',
            language: '',
            flow: '',
            tools: '',
            safety: '',
            rules: '',
          },
          voice_settings: {
            model_type: selectedModel,
            voice: selectedVoice,
            language: selectedLanguage,
            speech_speed: 1.0,
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
            temperature: 0.7,
            vad_threshold: 0.5,
            turn_detection: 'server_vad',
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
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Agent kaydedilemedi');
      }

      toast.success('Agent başarıyla kaydedildi');
      setHasChanges(false);
    } catch (error) {
      console.error('Save error:', error);
      toast.error(error instanceof Error ? error.message : 'Agent kaydedilirken bir hata oluştu');
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
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <Volume2 className="h-4 w-4" />
              Select Voice
              <ChevronDown className="h-4 w-4" />
            </button>
            
            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <Settings2 className="h-4 w-4" />
              Tools (0)
              <ChevronDown className="h-4 w-4" />
            </button>

            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              RAG
              <ChevronDown className="h-4 w-4" />
            </button>

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

      {/* Main Content - Split View */}
      <div className="flex-1 flex">
        {/* Left Panel - Editor */}
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
            {/* Prompt Tab */}
            {activeTab === 'prompt' && (
              <div className="p-4 space-y-3">
                {/* Header with AI button */}
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-muted-foreground">System Instructions</label>
                  <button
                    onClick={() => setIsPromptMakerOpen(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-violet-500/10 to-purple-600/10 hover:from-violet-500/20 hover:to-purple-600/20 border border-violet-500/30 text-violet-600 dark:text-violet-400 rounded-lg text-sm font-medium transition-all"
                  >
                    <Sparkles className="h-4 w-4" />
                    AI ile Oluştur
                  </button>
                </div>
                <textarea
                  value={prompt}
                  onChange={(e) => { setPrompt(e.target.value); setHasChanges(true); }}
                  placeholder="Enter your agent's prompt here..."
                  className="w-full h-[calc(100vh-200px)] p-4 bg-muted/30 rounded-xl text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 border border-border"
                />
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
                    placeholder="Merhaba {first_name}, ben {agent_name}. Size nasıl yardımcı olabilirim?"
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
                      💡 Excel&apos;den yüklenen özel sütunlar da değişken olarak kullanılabilir.
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

            {/* Settings Tab */}
            {activeTab === 'settings' && (
              <div className="p-6 space-y-6">
                {/* Voice Selection */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Voice</label>
                  <select
                    value={selectedVoice}
                    onChange={(e) => { setSelectedVoice(e.target.value); setHasChanges(true); }}
                    className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    {voices.map((voice) => (
                      <option key={voice.id} value={voice.id}>{voice.name}</option>
                    ))}
                  </select>
                </div>

                {/* Model Selection */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Model</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => { setSelectedModel(e.target.value); setHasChanges(true); }}
                    className="w-full px-4 py-2.5 bg-muted/30 rounded-lg text-sm border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value="gpt-realtime-mini">gpt-4o-realtime-preview-mini ($10/$20 per 1M tokens)</option>
                    <option value="gpt-realtime">gpt-4o-realtime-preview ($32/$64 per 1M tokens)</option>
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Mini model is more cost-effective for most use cases.
                  </p>
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

                {/* Record Calls */}
                <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border">
                  <div>
                    <p className="text-sm font-medium">Record Calls</p>
                    <p className="text-xs text-muted-foreground">Save audio recordings of all calls</p>
                  </div>
                  <button
                    onClick={() => { setRecordCalls(!recordCalls); setHasChanges(true); }}
                    className={cn(
                      'w-12 h-6 rounded-full transition-colors relative',
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
                      'w-12 h-6 rounded-full transition-colors relative',
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
            )}
          </div>

          {/* Footer - Agent ID */}
          <div className="px-4 py-2 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="font-mono">1D072ECF-1C23-406A-B1F4-31C480A4D...</span>
              <button className="hover:text-foreground transition-colors">
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
            <span>last saved: 5 hours ago</span>
          </div>
        </div>

        {/* Right Panel - Test */}
        <div className="w-[450px] flex-shrink-0 bg-background">
          <TestPanel />
        </div>
      </div>

      {/* AI Prompt Maker Modal */}
      <PromptMakerModal
        isOpen={isPromptMakerOpen}
        onClose={() => setIsPromptMakerOpen(false)}
        onGenerate={(generatedPrompt) => {
          setPrompt(generatedPrompt);
          setHasChanges(true);
        }}
        existingPrompt={prompt}
      />
    </div>
  );
}
