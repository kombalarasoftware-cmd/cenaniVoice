'use client';

import { cn } from '@/lib/utils';
import { X, Bot, Sparkles, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { API_V1 } from '@/lib/api';

interface CreateAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const templateColorClasses: Record<string, { bg: string; text: string }> = {
  primary: { bg: 'bg-primary-500/10', text: 'text-primary-500' },
  secondary: { bg: 'bg-secondary-500/10', text: 'text-secondary-500' },
  accent: { bg: 'bg-accent-500/10', text: 'text-accent-500' },
  success: { bg: 'bg-success-500/10', text: 'text-success-500' },
  warning: { bg: 'bg-warning-500/10', text: 'text-warning-500' },
  error: { bg: 'bg-error-500/10', text: 'text-error-500' },
};

const templates = [
  {
    id: 'blank',
    name: 'Blank Agent',
    description: 'Start from scratch with a blank canvas',
    icon: Bot,
    color: 'primary',
  },
  {
    id: 'payment-reminder',
    name: 'Payment Reminder',
    description: 'Remind customers about pending payments',
    icon: Sparkles,
    color: 'secondary',
  },
  {
    id: 'appointment-reminder',
    name: 'Appointment Reminder',
    description: 'Remind customers about upcoming appointments',
    icon: Sparkles,
    color: 'accent',
  },
  {
    id: 'survey',
    name: 'Customer Survey',
    description: 'Collect customer feedback and satisfaction scores',
    icon: Sparkles,
    color: 'success',
  },
  {
    id: 'lead-qualification',
    name: 'Lead Qualification',
    description: 'Qualify leads and schedule follow-ups',
    icon: Sparkles,
    color: 'warning',
  },
  {
    id: 'support',
    name: 'Customer Support',
    description: 'Handle basic support inquiries',
    icon: Sparkles,
    color: 'error',
  },
];

const languages = [
  { code: 'en', name: 'English' },
  { code: 'tr', name: 'Turkish' },
  { code: 'de', name: 'Deutsch' },
  { code: 'fr', name: 'Français' },
  { code: 'es', name: 'Español' },
  { code: 'it', name: 'Italiano' },
  { code: 'pt', name: 'Português' },
  { code: 'nl', name: 'Nederlands' },
  { code: 'pl', name: 'Polski' },
  { code: 'ru', name: 'Русский' },
  { code: 'ar', name: 'العربية' },
  { code: 'zh', name: '中文' },
  { code: 'ja', name: '日本語' },
  { code: 'ko', name: '한국어' },
];

const openaiVoices = [
  { id: 'alloy', name: 'Alloy', description: 'Neutral, balanced', gender: 'female' },
  { id: 'ash', name: 'Ash', description: 'Confident, clear', gender: 'male' },
  { id: 'ballad', name: 'Ballad', description: 'Warm, deep', gender: 'male' },
  { id: 'coral', name: 'Coral', description: 'Friendly, warm', gender: 'female' },
  { id: 'echo', name: 'Echo', description: 'Deep, resonant', gender: 'male' },
  { id: 'sage', name: 'Sage', description: 'Calm, wise', gender: 'female' },
  { id: 'shimmer', name: 'Shimmer', description: 'Soft, gentle', gender: 'female' },
  { id: 'verse', name: 'Verse', description: 'Dynamic, expressive', gender: 'male' },
  { id: 'marin', name: 'Marin ⭐', description: 'Natural, recommended', gender: 'female' },
  { id: 'cedar', name: 'Cedar ⭐', description: 'Natural, recommended', gender: 'male' },
];

const ultravoxVoices = [
  // Turkish
  { id: 'Cicek-Turkish', name: 'Cicek', description: 'TR, Female', gender: 'female' },
  { id: 'Doga-Turkish', name: 'Doga', description: 'TR, Male', gender: 'male' },
  // English
  { id: 'Mark', name: 'Mark', description: 'EN, Male', gender: 'male' },
  { id: 'Jessica', name: 'Jessica', description: 'EN, Female', gender: 'female' },
  { id: 'Sarah', name: 'Sarah', description: 'EN, Female', gender: 'female' },
  { id: 'Alex', name: 'Alex', description: 'EN, Male', gender: 'male' },
  { id: 'Carter', name: 'Carter', description: 'EN, Male (Cartesia)', gender: 'male' },
  { id: 'Olivia', name: 'Olivia', description: 'EN, Female', gender: 'female' },
  { id: 'Edward', name: 'Edward', description: 'EN, Male', gender: 'male' },
  { id: 'Luna', name: 'Luna', description: 'EN, Female', gender: 'female' },
  { id: 'Ashley', name: 'Ashley', description: 'EN, Female', gender: 'female' },
  { id: 'Dennis', name: 'Dennis', description: 'EN, Male', gender: 'male' },
  { id: 'Theodore', name: 'Theodore', description: 'EN, Male', gender: 'male' },
  { id: 'Julia', name: 'Julia', description: 'EN, Female', gender: 'female' },
  { id: 'Shaun', name: 'Shaun', description: 'EN, Male', gender: 'male' },
  { id: 'Hana', name: 'Hana', description: 'EN, Female', gender: 'female' },
  { id: 'Blake', name: 'Blake', description: 'EN, Male', gender: 'male' },
  { id: 'Timothy', name: 'Timothy', description: 'EN, Male', gender: 'male' },
  { id: 'Chelsea', name: 'Chelsea', description: 'EN, Female', gender: 'female' },
  { id: 'Emily-English', name: 'Emily', description: 'EN, Female', gender: 'female' },
  { id: 'Aaron-English', name: 'Aaron', description: 'EN, Male', gender: 'male' },
  // German
  { id: 'Josef', name: 'Josef', description: 'DE, Male', gender: 'male' },
  { id: 'Johanna', name: 'Johanna', description: 'DE, Female', gender: 'female' },
  { id: 'Ben-German', name: 'Ben', description: 'DE, Male', gender: 'male' },
  { id: 'Susi-German', name: 'Susi', description: 'DE, Female', gender: 'female' },
  // French
  { id: 'Hugo-French', name: 'Hugo', description: 'FR, Male', gender: 'male' },
  { id: 'Coco-French', name: 'Coco', description: 'FR, Female', gender: 'female' },
  { id: 'Alize-French', name: 'Alize', description: 'FR, Female', gender: 'female' },
  { id: 'Nicolas-French', name: 'Nicolas', description: 'FR, Male', gender: 'male' },
  // Spanish
  { id: 'Alex-Spanish', name: 'Alex', description: 'ES, Male', gender: 'male' },
  { id: 'Andrea-Spanish', name: 'Andrea', description: 'ES, Female', gender: 'female' },
  { id: 'Tatiana-Spanish', name: 'Tatiana', description: 'ES, Female', gender: 'female' },
  { id: 'Mauricio-Spanish', name: 'Mauricio', description: 'ES, Male', gender: 'male' },
  // Italian
  { id: 'Linda-Italian', name: 'Linda', description: 'IT, Female', gender: 'female' },
  { id: 'Giovanni-Italian', name: 'Giovanni', description: 'IT, Male', gender: 'male' },
  // Portuguese
  { id: 'Rosa-Portuguese', name: 'Rosa', description: 'PT-BR, Female', gender: 'female' },
  { id: 'Tiago-Portuguese', name: 'Tiago', description: 'PT-BR, Male', gender: 'male' },
  // Arabic
  { id: 'Salma-Arabic', name: 'Salma', description: 'AR, Female', gender: 'female' },
  { id: 'Raed-Arabic', name: 'Raed', description: 'AR-SA, Male', gender: 'male' },
  // Japanese
  { id: 'Morioki-Japanese', name: 'Morioki', description: 'JA, Male', gender: 'male' },
  { id: 'Asahi-Japanese', name: 'Asahi', description: 'JA, Female', gender: 'female' },
  // Korean
  { id: 'Yoona', name: 'Yoona', description: 'KO, Female', gender: 'female' },
  { id: 'Seojun', name: 'Seojun', description: 'KO, Male', gender: 'male' },
  // Chinese
  { id: 'Maya-Chinese', name: 'Maya', description: 'ZH, Female', gender: 'female' },
  { id: 'Martin-Chinese', name: 'Martin', description: 'ZH, Male', gender: 'male' },
  // Hindi
  { id: 'Riya-Hindi-Urdu', name: 'Riya', description: 'HI, Female', gender: 'female' },
  { id: 'Aakash-Hindi', name: 'Aakash', description: 'HI, Male', gender: 'male' },
  // Russian
  { id: 'Nadia-Russian', name: 'Nadia', description: 'RU, Female', gender: 'female' },
  { id: 'Felix-Russian', name: 'Felix', description: 'RU, Male', gender: 'male' },
  // Dutch
  { id: 'Ruth-Dutch', name: 'Ruth', description: 'NL, Female', gender: 'female' },
  { id: 'Daniel-Dutch', name: 'Daniel', description: 'NL, Male', gender: 'male' },
  // Ukrainian
  { id: 'Vira-Ukrainian', name: 'Vira', description: 'UK, Female', gender: 'female' },
  { id: 'Dmytro-Ukrainian', name: 'Dmytro', description: 'UK, Male', gender: 'male' },
  // Swedish
  { id: 'Sanna-Swedish', name: 'Sanna', description: 'SV, Female', gender: 'female' },
  { id: 'Adam-Swedish', name: 'Adam', description: 'SV, Male', gender: 'male' },
  // Polish
  { id: 'Hanna-Polish', name: 'Hanna', description: 'PL, Female', gender: 'female' },
  { id: 'Marcin-Polish', name: 'Marcin', description: 'PL, Male', gender: 'male' },
];

const pipelineVoices = [
  // Turkish
  { id: 'tr_TR-dfki-medium', name: 'Dfki', description: 'TR, Male', gender: 'male' },
  { id: 'tr_TR-fahrettin-medium', name: 'Fahrettin', description: 'TR, Male', gender: 'male' },
  { id: 'tr_TR-fettah-medium', name: 'Fettah', description: 'TR, Male', gender: 'male' },
  // English
  { id: 'en_US-amy-medium', name: 'Amy', description: 'EN, Female', gender: 'female' },
  { id: 'en_US-lessac-high', name: 'Lessac HQ', description: 'EN, Male, High Quality', gender: 'male' },
  { id: 'en_US-ryan-high', name: 'Ryan HQ', description: 'EN, Male, High Quality', gender: 'male' },
  { id: 'en_US-kristin-medium', name: 'Kristin', description: 'EN, Female', gender: 'female' },
  { id: 'en_GB-cori-high', name: 'Cori HQ', description: 'EN-GB, Female, High Quality', gender: 'female' },
  // German
  { id: 'de_DE-thorsten-medium', name: 'Thorsten', description: 'DE, Male', gender: 'male' },
  { id: 'de_DE-thorsten-high', name: 'Thorsten HQ', description: 'DE, Male, High Quality', gender: 'male' },
  { id: 'de_DE-thorsten_emotional-medium', name: 'Thorsten Emotional', description: 'DE, Male, Expressive', gender: 'male' },
  { id: 'de_DE-eva_k-x_low', name: 'Eva', description: 'DE, Female', gender: 'female' },
  { id: 'de_DE-kerstin-low', name: 'Kerstin', description: 'DE, Female', gender: 'female' },
  // French
  { id: 'fr_FR-siwis-medium', name: 'Siwis', description: 'FR, Female', gender: 'female' },
  { id: 'fr_FR-tom-medium', name: 'Tom', description: 'FR, Male', gender: 'male' },
  { id: 'fr_FR-gilles-low', name: 'Gilles', description: 'FR, Male', gender: 'male' },
  // Spanish
  { id: 'es_ES-sharvard-medium', name: 'Sharvard', description: 'ES, Male', gender: 'male' },
  { id: 'es_ES-davefx-medium', name: 'Davefx', description: 'ES, Male', gender: 'male' },
  { id: 'es_MX-claude-high', name: 'Claude HQ', description: 'ES-MX, Male, High Quality', gender: 'male' },
  // Italian
  { id: 'it_IT-riccardo-x_low', name: 'Riccardo', description: 'IT, Male', gender: 'male' },
  { id: 'it_IT-paola-medium', name: 'Paola', description: 'IT, Female', gender: 'female' },
];

const providers = [
  { id: 'openai', name: 'OpenAI Realtime', description: 'GPT-4o Realtime via Asterisk' },
  { id: 'ultravox', name: 'Ultravox', description: 'Native SIP, $0.05/min' },
  { id: 'pipeline', name: 'Pipeline (Local)', description: 'Local STT + LLM + TTS, $0/min' },
];

export function CreateAgentDialog({ open, onOpenChange }: CreateAgentDialogProps) {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [agentName, setAgentName] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [genderFilter, setGenderFilter] = useState<'all' | 'male' | 'female'>('all');
  const [isLoading, setIsLoading] = useState(false);

  const allVoices = selectedProvider === 'ultravox' ? ultravoxVoices : selectedProvider === 'pipeline' ? pipelineVoices : openaiVoices;
  const voices = genderFilter === 'all' ? allVoices : allVoices.filter(v => v.gender === genderFilter);

  const handleCreate = async () => {
    if (!agentName.trim()) {
      toast.error('Agent name is required');
      return;
    }

    setIsLoading(true);
    try {
      // Get token from localStorage (optional for dev mode)
      const token = localStorage.getItem('access_token');
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_V1}/agents`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: agentName.trim(),
          description: agentDescription.trim() || null,
          provider: selectedProvider,
          template: selectedTemplate,
          voice_settings: {
            voice: selectedVoice,
            language: selectedLanguage,
            speech_speed: 1.0,
            ...(selectedProvider === 'pipeline' ? { pipeline_voice: selectedVoice } : {}),
          },
          call_settings: {
            max_duration: 300,
            silence_timeout: 10,
            max_retries: 3,
            retry_delay: 30,
          },
          behavior_settings: {
            interruptible: true,
            auto_transcribe: true,
            record_calls: true,
            human_transfer: false,
          },
          advanced_settings: {
            temperature: 0.7,
            vad_threshold: 0.3,  // Lower = more sensitive to speech
            turn_detection: 'server_vad',
            silence_duration_ms: 800,
            prefix_padding_ms: 500,
            interrupt_response: true,
            create_response: true,
            noise_reduction: true,
          },
          prompt: {
            role: '',
            personality: '',
            language: '',
            flow: '',
            tools: '',
            safety: '',
            rules: '',
          },
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create agent');
      }

      const newAgent = await response.json();
      toast.success('Agent created successfully');
      router.push(`/dashboard/agents/${newAgent.id}`);
      onOpenChange(false);
      resetForm();
    } catch (error) {
      console.error('Agent creation error:', error);
      toast.error(error instanceof Error ? error.message : 'An error occurred while creating agent');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setStep(1);
    setSelectedTemplate(null);
    setAgentName('');
    setAgentDescription('');
    setSelectedProvider('openai');
    setSelectedLanguage('en');
    setSelectedVoice('alloy');
    setGenderFilter('all');
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => {
          onOpenChange(false);
          resetForm();
        }}
      />

      {/* Dialog */}
      <div
        className={cn(
          'relative w-full max-w-2xl max-h-[90vh] overflow-auto',
          'bg-card border border-border rounded-2xl shadow-2xl',
          'animate-scale-in custom-scrollbar'
        )}
      >
        {/* Header */}
        <div className="sticky top-0 bg-card border-b border-border px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Create New Agent</h2>
            <p className="text-sm text-muted-foreground">
              Step {step} of 2
            </p>
          </div>
          <button
            onClick={() => {
              onOpenChange(false);
              resetForm();
            }}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-4">Choose a Template</h3>
                <div className="grid grid-cols-2 gap-4">
                  {templates.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => setSelectedTemplate(template.id)}
                      className={cn(
                        'flex items-start gap-3 p-4 rounded-xl border text-left transition-all',
                        selectedTemplate === template.id
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <div
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-lg flex-shrink-0',
                          templateColorClasses[template.color]?.bg
                        )}
                      >
                        <template.icon
                          className={cn('h-5 w-5', templateColorClasses[template.color]?.text)}
                        />
                      </div>
                      <div>
                        <p className="font-medium">{template.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {template.description}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              {/* Agent Name */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Agent Name *
                </label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="e.g., Payment Reminder"
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                    'focus:border-primary-500 focus:outline-none transition-colors'
                  )}
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Description
                </label>
                <textarea
                  value={agentDescription}
                  onChange={(e) => setAgentDescription(e.target.value)}
                  placeholder="Briefly describe what this agent does..."
                  rows={3}
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                    'focus:border-primary-500 focus:outline-none transition-colors resize-none'
                  )}
                />
              </div>

              {/* Provider */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  AI Provider
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {providers.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => {
                        setSelectedProvider(p.id);
                        setSelectedVoice(p.id === 'ultravox' ? 'Mark' : p.id === 'pipeline' ? 'en_US-amy-medium' : 'alloy');
                        setGenderFilter('all');
                      }}
                      className={cn(
                        'p-3 rounded-lg border text-left transition-all',
                        selectedProvider === p.id
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <p className="font-medium">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Language */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Primary Language
                </label>
                <select
                  value={selectedLanguage}
                  onChange={(e) => setSelectedLanguage(e.target.value)}
                  className={cn(
                    'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                    'focus:border-primary-500 focus:outline-none transition-colors'
                  )}
                >
                  {languages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Voice */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium">Voice</label>
                  <div className="flex gap-1 bg-muted/30 rounded-lg p-0.5">
                    {[
                      { key: 'all' as const, label: 'All' },
                      { key: 'female' as const, label: '♀ Female' },
                      { key: 'male' as const, label: '♂ Male' },
                    ].map((f) => (
                      <button
                        key={f.key}
                        onClick={() => setGenderFilter(f.key)}
                        className={cn(
                          'px-2.5 py-1 text-xs rounded-md transition-all',
                          genderFilter === f.key
                            ? 'bg-primary-500 text-white shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2 max-h-48 overflow-auto custom-scrollbar">
                  {voices.map((voice) => (
                    <button
                      key={voice.id}
                      onClick={() => setSelectedVoice(voice.id)}
                      className={cn(
                        'p-2 rounded-lg border text-center transition-all',
                        selectedVoice === voice.id
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <p className="font-medium text-sm capitalize">{voice.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {voice.gender === 'male' ? '♂' : '♀'} {voice.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-card border-t border-border px-6 py-4 flex items-center justify-between">
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              className="px-4 py-2 rounded-lg text-muted-foreground hover:text-foreground transition-colors"
            >
              Back
            </button>
          ) : (
            <div />
          )}

          {step === 1 ? (
            <button
              onClick={() => setStep(2)}
              disabled={!selectedTemplate}
              className={cn(
                'px-6 py-2 rounded-lg font-medium transition-colors',
                selectedTemplate
                  ? 'bg-primary-500 hover:bg-primary-600 text-white'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              )}
            >
              Continue
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={!agentName.trim() || isLoading}
              className={cn(
                'px-6 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
                agentName.trim() && !isLoading
                  ? 'bg-primary-500 hover:bg-primary-600 text-white'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              )}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? 'Creating...' : 'Create Agent'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
