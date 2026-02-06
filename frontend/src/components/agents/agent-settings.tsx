'use client';

import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  Volume2,
  Globe,
  Clock,
  Phone,
  Webhook,
  Database,
  Shield,
  Settings2,
  ChevronDown,
  Play,
  Pause,
} from 'lucide-react';

interface AgentSettingsProps {
  onChange: () => void;
}

const languages = [
  { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'pt', name: 'Português', flag: '🇵🇹' },
  { code: 'nl', name: 'Nederlands', flag: '🇳🇱' },
  { code: 'ar', name: 'العربية', flag: '🇸🇦' },
  { code: 'zh', name: '中文', flag: '🇨🇳' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
  { code: 'ko', name: '한국어', flag: '🇰🇷' },
];

const voices = [
  { id: 'alloy', name: 'Alloy', description: 'Neutral and balanced', gender: 'neutral' },
  { id: 'echo', name: 'Echo', description: 'Deep and authoritative', gender: 'male' },
  { id: 'fable', name: 'Fable', description: 'Warm and expressive', gender: 'neutral' },
  { id: 'onyx', name: 'Onyx', description: 'Deep and rich', gender: 'male' },
  { id: 'nova', name: 'Nova', description: 'Friendly and upbeat', gender: 'female' },
  { id: 'shimmer', name: 'Shimmer', description: 'Soft and gentle', gender: 'female' },
];

export function AgentSettings({ onChange }: AgentSettingsProps) {
  const [settings, setSettings] = useState({
    // Voice settings
    voice: 'alloy',
    language: 'tr',
    speechSpeed: 1.0,
    
    // Call settings
    maxDuration: 300, // seconds
    silenceTimeout: 10, // seconds
    maxRetries: 3,
    retryDelay: 60, // minutes
    
    // Behavior settings
    interruptible: true,
    autoTranscribe: true,
    recordCalls: true,
    humanTransfer: true,
    
    // Advanced settings
    temperature: 0.7,
    vadThreshold: 0.5,
    turnDetection: 'server_vad',
  });

  const [playingVoice, setPlayingVoice] = useState<string | null>(null);

  const updateSetting = (key: string, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    onChange();
  };

  const playVoiceSample = (voiceId: string) => {
    if (playingVoice === voiceId) {
      setPlayingVoice(null);
    } else {
      setPlayingVoice(voiceId);
      // Simulate playing
      setTimeout(() => setPlayingVoice(null), 2000);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Voice Settings */}
      <div className="p-6 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/10">
            <Volume2 className="h-5 w-5 text-primary-500" />
          </div>
          <div>
            <h3 className="font-semibold">Voice Settings</h3>
            <p className="text-sm text-muted-foreground">
              Configure the AI voice and speech parameters
            </p>
          </div>
        </div>

        <div className="space-y-6">
          {/* Voice selection */}
          <div>
            <label className="block text-sm font-medium mb-3">Voice</label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {voices.map((voice) => (
                <button
                  key={voice.id}
                  onClick={() => updateSetting('voice', voice.id)}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-lg border transition-all',
                    settings.voice === voice.id
                      ? 'border-primary-500 bg-primary-500/5'
                      : 'border-border hover:border-primary-500/50'
                  )}
                >
                  <div className="text-left">
                    <p className="font-medium capitalize">{voice.name}</p>
                    <p className="text-xs text-muted-foreground">{voice.description}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      playVoiceSample(voice.id);
                    }}
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-full',
                      'bg-muted hover:bg-muted/80 transition-colors'
                    )}
                  >
                    {playingVoice === voice.id ? (
                      <Pause className="h-4 w-4 text-primary-500" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </button>
                </button>
              ))}
            </div>
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium mb-3">Primary Language</label>
            <div className="grid grid-cols-3 md:grid-cols-4 gap-2">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => updateSetting('language', lang.code)}
                  className={cn(
                    'flex items-center gap-2 p-2.5 rounded-lg border text-sm transition-all',
                    settings.language === lang.code
                      ? 'border-primary-500 bg-primary-500/5'
                      : 'border-border hover:border-primary-500/50'
                  )}
                >
                  <span>{lang.flag}</span>
                  <span className="font-medium">{lang.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Speech speed */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-medium">Speech Speed</label>
              <span className="text-sm text-muted-foreground">{settings.speechSpeed}x</span>
            </div>
            <input
              type="range"
              min={0.5}
              max={2}
              step={0.1}
              value={settings.speechSpeed}
              onChange={(e) => updateSetting('speechSpeed', parseFloat(e.target.value))}
              className="w-full accent-primary-500"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>0.5x (Slow)</span>
              <span>1x (Normal)</span>
              <span>2x (Fast)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Call Settings */}
      <div className="p-6 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary-500/10">
            <Phone className="h-5 w-5 text-secondary-500" />
          </div>
          <div>
            <h3 className="font-semibold">Call Settings</h3>
            <p className="text-sm text-muted-foreground">
              Configure call behavior and limits
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Max duration */}
          <div>
            <label className="block text-sm font-medium mb-2">Max Call Duration</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={settings.maxDuration}
                onChange={(e) => updateSetting('maxDuration', parseInt(e.target.value))}
                className={cn(
                  'flex-1 px-4 py-2.5 rounded-lg bg-background border border-border',
                  'focus:border-primary-500 focus:outline-none transition-colors'
                )}
              />
              <span className="text-sm text-muted-foreground">seconds</span>
            </div>
          </div>

          {/* Silence timeout */}
          <div>
            <label className="block text-sm font-medium mb-2">Silence Timeout</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={settings.silenceTimeout}
                onChange={(e) => updateSetting('silenceTimeout', parseInt(e.target.value))}
                className={cn(
                  'flex-1 px-4 py-2.5 rounded-lg bg-background border border-border',
                  'focus:border-primary-500 focus:outline-none transition-colors'
                )}
              />
              <span className="text-sm text-muted-foreground">seconds</span>
            </div>
          </div>

          {/* Max retries */}
          <div>
            <label className="block text-sm font-medium mb-2">Max Retries per Day</label>
            <input
              type="number"
              value={settings.maxRetries}
              onChange={(e) => updateSetting('maxRetries', parseInt(e.target.value))}
              className={cn(
                'w-full px-4 py-2.5 rounded-lg bg-background border border-border',
                'focus:border-primary-500 focus:outline-none transition-colors'
              )}
            />
          </div>

          {/* Retry delay */}
          <div>
            <label className="block text-sm font-medium mb-2">Retry Delay</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={settings.retryDelay}
                onChange={(e) => updateSetting('retryDelay', parseInt(e.target.value))}
                className={cn(
                  'flex-1 px-4 py-2.5 rounded-lg bg-background border border-border',
                  'focus:border-primary-500 focus:outline-none transition-colors'
                )}
              />
              <span className="text-sm text-muted-foreground">minutes</span>
            </div>
          </div>
        </div>
      </div>

      {/* Behavior Settings */}
      <div className="p-6 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-500/10">
            <Settings2 className="h-5 w-5 text-accent-500" />
          </div>
          <div>
            <h3 className="font-semibold">Behavior Settings</h3>
            <p className="text-sm text-muted-foreground">
              Control how the agent behaves during calls
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {[
            {
              key: 'interruptible',
              label: 'Allow Interruption',
              description: 'Customer can interrupt while AI is speaking',
            },
            {
              key: 'autoTranscribe',
              label: 'Auto Transcription',
              description: 'Automatically transcribe all conversations',
            },
            {
              key: 'recordCalls',
              label: 'Record Calls',
              description: 'Save audio recordings of all calls',
            },
            {
              key: 'humanTransfer',
              label: 'Enable Human Transfer',
              description: 'Allow transfer to human agents when needed',
            },
          ].map((item) => (
            <div
              key={item.key}
              className="flex items-center justify-between p-4 rounded-lg bg-muted/30"
            >
              <div>
                <p className="font-medium">{item.label}</p>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
              <button
                onClick={() =>
                  updateSetting(item.key, !settings[item.key as keyof typeof settings])
                }
                className={cn(
                  'relative w-12 h-6 rounded-full transition-colors',
                  settings[item.key as keyof typeof settings]
                    ? 'bg-primary-500'
                    : 'bg-muted'
                )}
              >
                <div
                  className={cn(
                    'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                    settings[item.key as keyof typeof settings]
                      ? 'translate-x-7'
                      : 'translate-x-1'
                  )}
                />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Advanced Settings */}
      <div className="p-6 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-warning-500/10">
            <Shield className="h-5 w-5 text-warning-500" />
          </div>
          <div>
            <h3 className="font-semibold">Advanced Settings</h3>
            <p className="text-sm text-muted-foreground">
              Fine-tune AI behavior parameters
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Temperature */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">Temperature</label>
              <span className="text-sm text-muted-foreground">{settings.temperature}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={settings.temperature}
              onChange={(e) => updateSetting('temperature', parseFloat(e.target.value))}
              className="w-full accent-primary-500"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>Focused</span>
              <span>Creative</span>
            </div>
          </div>

          {/* VAD Threshold */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">VAD Sensitivity</label>
              <span className="text-sm text-muted-foreground">{settings.vadThreshold}</span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.1}
              value={settings.vadThreshold}
              onChange={(e) => updateSetting('vadThreshold', parseFloat(e.target.value))}
              className="w-full accent-primary-500"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>

          {/* Turn detection */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-2">Turn Detection Mode</label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: 'server_vad', name: 'Server VAD', description: 'Server-side voice detection' },
                { id: 'semantic', name: 'Semantic', description: 'AI determines turn boundaries' },
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => updateSetting('turnDetection', mode.id)}
                  className={cn(
                    'p-4 rounded-lg border text-left transition-all',
                    settings.turnDetection === mode.id
                      ? 'border-primary-500 bg-primary-500/5'
                      : 'border-border hover:border-primary-500/50'
                  )}
                >
                  <p className="font-medium">{mode.name}</p>
                  <p className="text-sm text-muted-foreground">{mode.description}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
