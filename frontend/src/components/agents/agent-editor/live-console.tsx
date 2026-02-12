'use client';

import { cn } from '@/lib/utils';
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Loader2,
  Clipboard,
  Bot,
  User,
  RotateCcw,
  X,
} from 'lucide-react';
import { CallMetricsCompact } from './call-metrics';
import { toast } from 'sonner';
import { useCall } from '@/components/providers/call-provider';

interface ProviderInfo {
  provider: string;
  voice?: string;
  model?: string;
}

interface LiveConsoleProps {
  agentId: string;
  providerInfo?: ProviderInfo;
  onCallStart?: (callId: string) => void;
  onCallEnd?: () => void;
  onClose?: () => void;
  className?: string;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export function LiveConsole({ agentId, providerInfo, onCallStart, onCallEnd, onClose, className }: LiveConsoleProps) {
  // All call state from global context (persists across navigation)
  const {
    callStatus,
    callId,
    phoneNumber,
    setPhoneNumber,
    customerName,
    setCustomerName,
    customerTitle,
    setCustomerTitle,
    isMuted,
    setIsMuted,
    isAudioMuted,
    setIsAudioMuted,
    messages,
    metrics,
    cost,
    isUserSpeaking,
    isAgentSpeaking,
    startCall,
    endCall,
    resetCall,
  } = useCall();

  const handleStartCall = async () => {
    if (!phoneNumber.trim()) {
      toast.error('Please enter a phone number');
      return;
    }
    await startCall({
      phoneNumber,
      agentId,
      customerName: customerName || undefined,
      customerTitle: customerTitle || undefined,
    });
    onCallStart?.(callId || '');
  };

  const handleEndCall = async () => {
    await endCall();
    onCallEnd?.();
  };

  const handleNewCall = () => {
    resetCall();
  };

  const handlePastePhone = async () => {
    try {
      const text = await navigator.clipboard.readText();
      const cleaned = text.replace(/[\s\-\(\)]/g, '');
      if (/^\+?[0-9]{10,15}$/.test(cleaned)) {
        setPhoneNumber(cleaned);
        toast.success('Number pasted');
      } else {
        toast.error('Invalid phone number');
      }
    } catch {
      toast.error('Failed to paste');
    }
  };

  const isIdle = callStatus === 'idle' || callStatus === 'ended';

  return (
    <div className={cn('flex items-start justify-center py-6', className)}>
      {/* Phone Frame */}
      <div className="w-full max-w-[420px] rounded-3xl border-2 border-border bg-card shadow-2xl overflow-hidden">

        {/* Status Bar */}
        <div className="flex items-center justify-between px-5 py-3 bg-muted/30 border-b border-border">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold">Test Console</span>
            {onClose && (
              <button
                onClick={onClose}
                className="flex h-6 w-6 items-center justify-center rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                title="Close"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          {callStatus === 'connected' && (
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
              </span>
              <span className="text-xs font-medium text-red-500">LIVE</span>
            </div>
          )}
          {callStatus === 'ended' && (
            <span className="text-xs font-medium text-muted-foreground">Call Ended</span>
          )}
        </div>

        {/* Caller Display */}
        <div className="flex flex-col items-center py-6 px-5">
          <div className={cn(
            'flex h-20 w-20 items-center justify-center rounded-full transition-all duration-300',
            callStatus === 'connected'
              ? 'bg-green-500/10 ring-4 ring-green-500/20'
              : callStatus === 'connecting'
                ? 'bg-yellow-500/10 ring-4 ring-yellow-500/20 animate-pulse'
                : 'bg-muted'
          )}>
            {callStatus === 'connecting' ? (
              <Loader2 className="h-10 w-10 text-yellow-500 animate-spin" />
            ) : (
              <Phone className={cn(
                'h-10 w-10',
                callStatus === 'connected' ? 'text-green-500' : 'text-muted-foreground'
              )} />
            )}
          </div>

          <div className="mt-3 text-center">
            {customerName && callStatus !== 'idle' ? (
              <p className="text-lg font-semibold">
                {customerName}{customerTitle ? ` ${customerTitle}` : ''}
              </p>
            ) : callStatus === 'idle' ? (
              <p className="text-lg font-semibold text-muted-foreground">Enter Details</p>
            ) : null}

            {phoneNumber && callStatus !== 'idle' && (
              <p className="text-sm text-muted-foreground">{phoneNumber}</p>
            )}

            {callStatus === 'connecting' && (
              <p className="text-sm text-yellow-500 mt-1">Connecting...</p>
            )}
            {callStatus === 'connected' && (
              <p className="text-sm text-green-500 font-medium mt-1">
                {formatDuration(metrics.duration)}
              </p>
            )}
            {callStatus === 'ended' && (
              <p className="text-sm text-muted-foreground mt-1">
                Duration: {formatDuration(metrics.duration)}
              </p>
            )}
          </div>
        </div>

        {/* Input Fields - only when idle */}
        {isIdle && (
          <div className="px-5 pb-4 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Customer Name (optional)"
                className="flex-1 px-4 py-2.5 rounded-xl border border-border bg-background
                         focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
              <select
                value={customerTitle}
                onChange={(e) => setCustomerTitle(e.target.value as '' | 'Mr' | 'Mrs')}
                className="w-24 px-2 py-2.5 rounded-xl border border-border bg-background
                         focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm text-center"
              >
                <option value="">Title</option>
                <option value="Mr">Mr</option>
                <option value="Mrs">Mrs</option>
              </select>
            </div>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="Phone Number"
                className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-border bg-background
                         focus:outline-none focus:ring-2 focus:ring-primary-500 text-sm"
              />
              <button
                onClick={handlePastePhone}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-muted transition-colors"
                title="Paste"
              >
                <Clipboard className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          </div>
        )}

        {/* Speaking Indicators - only when connected */}
        {callStatus === 'connected' && (
          <div className="flex items-center justify-center gap-4 px-5 pb-3">
            <div className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
              isUserSpeaking
                ? 'bg-blue-500/15 text-blue-500 ring-1 ring-blue-500/30'
                : 'bg-muted/50 text-muted-foreground'
            )}>
              <User className="h-3.5 w-3.5" />
              Customer
              {isUserSpeaking && (
                <span className="flex gap-0.5">
                  <span className="w-1 h-3 bg-blue-500 rounded-full animate-pulse" />
                  <span className="w-1 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-3.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                </span>
              )}
            </div>
            <div className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
              isAgentSpeaking
                ? 'bg-primary-500/15 text-primary-500 ring-1 ring-primary-500/30'
                : 'bg-muted/50 text-muted-foreground'
            )}>
              <Bot className="h-3.5 w-3.5" />
              Agent
              {isAgentSpeaking && (
                <span className="flex gap-0.5">
                  <span className="w-1 h-3 bg-primary-500 rounded-full animate-pulse" />
                  <span className="w-1 h-2 bg-primary-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-1 h-3.5 bg-primary-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                </span>
              )}
            </div>
          </div>
        )}

        {/* Call Controls */}
        <div className="flex items-center justify-center gap-5 py-5 px-5">
          {isIdle ? (
            <>
              {/* Call Button */}
              <button
                onClick={handleStartCall}
                disabled={!phoneNumber.trim()}
                className={cn(
                  'flex items-center justify-center w-16 h-16 rounded-full transition-all shadow-lg',
                  phoneNumber.trim()
                    ? 'bg-green-500 hover:bg-green-600 text-white shadow-green-500/25 hover:shadow-green-500/40 hover:scale-105'
                    : 'bg-muted text-muted-foreground cursor-not-allowed'
                )}
              >
                <Phone className="h-7 w-7" />
              </button>

              {/* New Call button after ended */}
              {callStatus === 'ended' && (
                <button
                  onClick={handleNewCall}
                  className="flex items-center justify-center w-12 h-12 rounded-full bg-muted hover:bg-muted/80 transition-all"
                  title="Reset"
                >
                  <RotateCcw className="h-5 w-5 text-muted-foreground" />
                </button>
              )}
            </>
          ) : callStatus === 'connecting' ? (
            <button
              disabled
              className="flex items-center justify-center w-16 h-16 rounded-full bg-yellow-500 text-white animate-pulse"
            >
              <Loader2 className="h-7 w-7 animate-spin" />
            </button>
          ) : (
            <>
              {/* Mute */}
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={cn(
                  'flex items-center justify-center w-12 h-12 rounded-full transition-all',
                  isMuted
                    ? 'bg-red-500/15 text-red-500 ring-1 ring-red-500/30'
                    : 'bg-muted hover:bg-muted/80 text-muted-foreground'
                )}
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </button>

              {/* Hangup */}
              <button
                onClick={handleEndCall}
                className="flex items-center justify-center w-16 h-16 rounded-full bg-red-500 hover:bg-red-600 text-white transition-all shadow-lg shadow-red-500/25 hover:shadow-red-500/40 hover:scale-105"
              >
                <PhoneOff className="h-7 w-7" />
              </button>

              {/* Speaker */}
              <button
                onClick={() => setIsAudioMuted(!isAudioMuted)}
                className={cn(
                  'flex items-center justify-center w-12 h-12 rounded-full transition-all',
                  isAudioMuted
                    ? 'bg-red-500/15 text-red-500 ring-1 ring-red-500/30'
                    : 'bg-muted hover:bg-muted/80 text-muted-foreground'
                )}
                title={isAudioMuted ? 'Unmute Audio' : 'Mute Audio'}
              >
                {isAudioMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
              </button>
            </>
          )}
        </div>

        {/* Provider Info Badge */}
        {providerInfo && (
          <div className="px-5 py-2.5 border-t border-border bg-muted/10">
            {providerInfo.provider === 'openai' ? (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">OpenAI Realtime</span>
                <div className="flex items-center gap-3">
                  <span className="font-medium font-mono text-[10px]">{providerInfo.model || 'gpt-4o-realtime'}</span>
                  <span className="text-muted-foreground">|</span>
                  <span className="font-medium capitalize">{providerInfo.voice || 'alloy'}</span>
                </div>
              </div>
            ) : providerInfo.provider === 'xai' ? (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">xAI Grok</span>
                <div className="flex items-center gap-3">
                  <span className="font-medium font-mono text-[10px]">{providerInfo.model || 'grok-2-realtime'}</span>
                  <span className="text-muted-foreground">|</span>
                  <span className="font-medium capitalize">{providerInfo.voice || 'Ara'}</span>
                </div>
              </div>
            ) : providerInfo.provider === 'gemini' ? (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Google Gemini</span>
                <div className="flex items-center gap-3">
                  <span className="font-medium font-mono text-[10px]">{providerInfo.model || 'gemini-live'}</span>
                  <span className="text-muted-foreground">|</span>
                  <span className="font-medium capitalize">{providerInfo.voice || 'Kore'}</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground">Ultravox</span>
                <div className="flex items-center gap-3">
                  <span className="font-medium font-mono text-[10px]">{providerInfo.model || 'ultravox'}</span>
                  <span className="text-muted-foreground">|</span>
                  <span className="font-medium capitalize">{providerInfo.voice || '-'}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Metrics Footer */}
        {(callStatus === 'connected' || callStatus === 'ended') && (
          <div className="px-5 py-3 border-t border-border bg-muted/20">
            <CallMetricsCompact
              metrics={metrics}
              cost={cost}
              isActive={callStatus === 'connected'}
              className="justify-center"
            />
          </div>
        )}
      </div>
    </div>
  );
}
