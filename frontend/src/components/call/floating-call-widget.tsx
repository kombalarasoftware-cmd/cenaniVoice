'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { cn, formatDuration } from '@/lib/utils';
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  ChevronUp,
  ChevronDown,
  Bot,
  User,
  Loader2,
  X,
} from 'lucide-react';
import { useCall } from '@/components/providers/call-provider';

export function FloatingCallWidget() {
  const {
    callStatus,
    phoneNumber,
    customerName,
    customerTitle,
    messages,
    metrics,
    cost,
    isUserSpeaking,
    isAgentSpeaking,
    isMuted,
    setIsMuted,
    isAudioMuted,
    setIsAudioMuted,
    endCall,
    resetCall,
  } = useCall();

  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  // Don't show if no active call
  const isCallActive = callStatus === 'connecting' || callStatus === 'connected';
  if (!isCallActive) return null;

  // Don't show if user is viewing the full console (agent editor with console tab)
  // The agent editor page is at /dashboard/agents/[id] - check if we're there
  const isOnAgentEditor = /^\/dashboard\/agents\/[^/]+$/.test(pathname);
  if (isOnAgentEditor) return null;

  const displayName = customerName
    ? `${customerName}${customerTitle ? ` ${customerTitle}` : ''}`
    : phoneNumber;

  return (
    <div
      className={cn(
        'fixed bottom-6 right-6 z-50 transition-all duration-300 ease-in-out',
        'animate-in slide-in-from-bottom-4 fade-in'
      )}
    >
      <div
        className={cn(
          'rounded-2xl border-2 bg-card shadow-2xl overflow-hidden transition-all duration-300',
          callStatus === 'connected'
            ? 'border-green-500/40 shadow-green-500/10'
            : 'border-yellow-500/40 shadow-yellow-500/10',
          expanded ? 'w-80' : 'w-72'
        )}
      >
        {/* Header - always visible */}
        <div
          className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-muted/30 transition-colors"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-center gap-3 min-w-0">
            {/* Status indicator */}
            <div className={cn(
              'flex h-10 w-10 items-center justify-center rounded-full flex-shrink-0',
              callStatus === 'connected'
                ? 'bg-green-500/10 ring-2 ring-green-500/30'
                : 'bg-yellow-500/10 ring-2 ring-yellow-500/30 animate-pulse'
            )}>
              {callStatus === 'connecting' ? (
                <Loader2 className="h-5 w-5 text-yellow-500 animate-spin" />
              ) : (
                <Phone className="h-5 w-5 text-green-500" />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold truncate">{displayName}</p>
                {callStatus === 'connected' && (
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                    </span>
                    <span className="text-[10px] font-bold text-red-500">LIVE</span>
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {callStatus === 'connecting' ? 'Connecting...' : formatDuration(metrics.duration)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {expanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronUp className="h-4 w-4 text-muted-foreground" />
            )}
          </div>
        </div>

        {/* Speaking indicators */}
        {callStatus === 'connected' && (
          <div className="flex items-center justify-center gap-3 px-4 pb-2">
            <div className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium transition-all',
              isUserSpeaking
                ? 'bg-blue-500/15 text-blue-500'
                : 'bg-muted/50 text-muted-foreground'
            )}>
              <User className="h-3 w-3" />
              Customer
              {isUserSpeaking && (
                <span className="flex gap-0.5">
                  <span className="w-0.5 h-2 bg-blue-500 rounded-full animate-pulse" />
                  <span className="w-0.5 h-1.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-0.5 h-2.5 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                </span>
              )}
            </div>
            <div className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium transition-all',
              isAgentSpeaking
                ? 'bg-primary-500/15 text-primary-500'
                : 'bg-muted/50 text-muted-foreground'
            )}>
              <Bot className="h-3 w-3" />
              Agent
              {isAgentSpeaking && (
                <span className="flex gap-0.5">
                  <span className="w-0.5 h-2 bg-primary-500 rounded-full animate-pulse" />
                  <span className="w-0.5 h-1.5 bg-primary-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                  <span className="w-0.5 h-2.5 bg-primary-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                </span>
              )}
            </div>
          </div>
        )}

        {/* Controls */}
        <div className="flex items-center justify-center gap-3 px-4 py-2 border-t border-border">
          {/* Mute */}
          <button
            onClick={(e) => { e.stopPropagation(); setIsMuted(!isMuted); }}
            className={cn(
              'flex items-center justify-center w-9 h-9 rounded-full transition-all',
              isMuted
                ? 'bg-red-500/15 text-red-500 ring-1 ring-red-500/30'
                : 'bg-muted hover:bg-muted/80 text-muted-foreground'
            )}
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </button>

          {/* Hangup */}
          <button
            onClick={(e) => { e.stopPropagation(); endCall(); }}
            className="flex items-center justify-center w-11 h-11 rounded-full bg-red-500 hover:bg-red-600 text-white transition-all shadow-lg shadow-red-500/25 hover:scale-105"
          >
            <PhoneOff className="h-5 w-5" />
          </button>

          {/* Speaker */}
          <button
            onClick={(e) => { e.stopPropagation(); setIsAudioMuted(!isAudioMuted); }}
            className={cn(
              'flex items-center justify-center w-9 h-9 rounded-full transition-all',
              isAudioMuted
                ? 'bg-red-500/15 text-red-500 ring-1 ring-red-500/30'
                : 'bg-muted hover:bg-muted/80 text-muted-foreground'
            )}
            title={isAudioMuted ? 'Unmute Audio' : 'Mute Audio'}
          >
            {isAudioMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
        </div>

        {/* Expanded: Transcript */}
        {expanded && callStatus === 'connected' && (
          <div className="border-t border-border">
            <div className="max-h-48 overflow-y-auto p-3 space-y-2 custom-scrollbar">
              {messages.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">
                  Waiting for conversation...
                </p>
              ) : (
                messages.slice(-10).map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      'flex gap-2 text-xs',
                      msg.role === 'assistant' ? 'justify-start' : 'justify-end'
                    )}
                  >
                    {msg.role === 'assistant' && (
                      <Bot className="h-3.5 w-3.5 text-primary-500 flex-shrink-0 mt-0.5" />
                    )}
                    <span
                      className={cn(
                        'px-2.5 py-1.5 rounded-xl max-w-[85%]',
                        msg.role === 'assistant'
                          ? 'bg-muted text-foreground'
                          : 'bg-primary-500/10 text-primary-500',
                        msg.interrupted && 'opacity-60 line-through'
                      )}
                    >
                      {msg.content}
                    </span>
                    {msg.role === 'user' && (
                      <User className="h-3.5 w-3.5 text-blue-500 flex-shrink-0 mt-0.5" />
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Mini metrics */}
            <div className="flex items-center justify-between px-3 py-2 border-t border-border bg-muted/20 text-[10px] text-muted-foreground">
              <span>{metrics.turnCount} turns</span>
              <span>{metrics.interrupts} interrupts</span>
              {cost && <span>${cost.cost.total.toFixed(4)}</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
