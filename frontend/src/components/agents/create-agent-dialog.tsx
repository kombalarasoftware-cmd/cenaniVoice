'use client';

import { cn } from '@/lib/utils';
import { X, Bot, Sparkles, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

interface CreateAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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
  { code: 'tr', name: 'Türkçe' },
  { code: 'en', name: 'English' },
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

const voices = [
  { id: 'alloy', name: 'Alloy', description: 'Neutral and balanced' },
  { id: 'echo', name: 'Echo', description: 'Deep and authoritative' },
  { id: 'fable', name: 'Fable', description: 'Warm and expressive' },
  { id: 'onyx', name: 'Onyx', description: 'Deep and rich' },
  { id: 'nova', name: 'Nova', description: 'Friendly and upbeat' },
  { id: 'shimmer', name: 'Shimmer', description: 'Soft and gentle' },
];

export function CreateAgentDialog({ open, onOpenChange }: CreateAgentDialogProps) {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [agentName, setAgentName] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('tr');
  const [selectedVoice, setSelectedVoice] = useState('alloy');
  const [isLoading, setIsLoading] = useState(false);

  const handleCreate = async () => {
    if (!agentName.trim()) {
      toast.error('Agent adı zorunludur');
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

      const response = await fetch('http://localhost:8000/api/v1/agents', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: agentName.trim(),
          description: agentDescription.trim() || null,
          template: selectedTemplate,
          voice_settings: {
            voice: selectedVoice,
            language: selectedLanguage,
            speech_speed: 1.0,
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
            vad_threshold: 0.5,
            turn_detection: 'server_vad',
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
        throw new Error(error.detail || 'Agent oluşturulamadı');
      }

      const newAgent = await response.json();
      toast.success('Agent başarıyla oluşturuldu');
      router.push(`/dashboard/agents/${newAgent.id}`);
      onOpenChange(false);
      resetForm();
    } catch (error) {
      console.error('Agent creation error:', error);
      toast.error(error instanceof Error ? error.message : 'Agent oluşturulurken bir hata oluştu');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setStep(1);
    setSelectedTemplate(null);
    setAgentName('');
    setAgentDescription('');
    setSelectedLanguage('tr');
    setSelectedVoice('alloy');
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
                          `bg-${template.color}-500/10`
                        )}
                      >
                        <template.icon
                          className={cn('h-5 w-5', `text-${template.color}-500`)}
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
                  placeholder="e.g., Ödeme Hatırlatıcı"
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
                <label className="block text-sm font-medium mb-2">
                  Voice
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {voices.map((voice) => (
                    <button
                      key={voice.id}
                      onClick={() => setSelectedVoice(voice.id)}
                      className={cn(
                        'p-3 rounded-lg border text-center transition-all',
                        selectedVoice === voice.id
                          ? 'border-primary-500 bg-primary-500/5'
                          : 'border-border hover:border-primary-500/50'
                      )}
                    >
                      <p className="font-medium capitalize">{voice.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {voice.description}
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
