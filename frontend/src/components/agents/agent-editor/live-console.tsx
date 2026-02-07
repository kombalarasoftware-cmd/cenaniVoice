'use client';

import { cn } from '@/lib/utils';
import { useState, useRef, useEffect } from 'react';
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Loader2,
  Clipboard,
} from 'lucide-react';
import { AudioWaveform } from './audio-waveform';
import { CallMetricsCompact, CallMetrics, CostBreakdown } from './call-metrics';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  interrupted?: boolean;
}

interface LiveConsoleProps {
  agentId: string;
  onCallStart?: (callId: string) => void;
  onCallEnd?: () => void;
  className?: string;
}

export function LiveConsole({ agentId, onCallStart, onCallEnd, className }: LiveConsoleProps) {
  // Call state
  const [callStatus, setCallStatus] = useState<'idle' | 'connecting' | 'connected' | 'ended'>('idle');
  const [callId, setCallId] = useState<string | null>(null);  // AudioSocket UUID - for SSE events & transcript
  const [channelId, setChannelId] = useState<string | null>(null);  // Asterisk channel ID - for hangup
  const [phoneNumber, setPhoneNumber] = useState('');
  const [customerName, setCustomerName] = useState('');  // Customer name for personalization
  const [isMuted, setIsMuted] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  
  // Data state
  const [messages, setMessages] = useState<Message[]>([]);
  const [metrics, setMetrics] = useState<CallMetrics>({
    duration: 0,
    latency: 0,
    interrupts: 0,
    turnCount: 0,
  });
  
  // UI state
  const durationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // Speaking state - based on transcript activity
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const lastMessageCountRef = useRef(0);
  const speakingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Cost tracking
  const [cost, setCost] = useState<CostBreakdown | null>(null);
  
  // SSE EventSource ref
  const eventSourceRef = useRef<EventSource | null>(null);

  // Duration timer
  useEffect(() => {
    if (callStatus === 'connected') {
      durationIntervalRef.current = setInterval(() => {
        setMetrics(prev => ({ ...prev, duration: prev.duration + 1 }));
      }, 1000);
    }
    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
    };
  }, [callStatus]);

  // Fetch transcript during call
  useEffect(() => {
    if (!callId || callStatus !== 'connected') return;
    
    const fetchTranscript = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`http://localhost:8000/api/v1/calls/${callId}/transcript`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data.transcript && Array.isArray(data.transcript)) {
            const newMessages: Message[] = data.transcript.map((t: { role: string; text?: string; content?: string }, i: number) => ({
              id: `${callId}-${i}`,
              role: (t.role === 'agent' || t.role === 'assistant') ? 'assistant' : 'user',
              content: t.content || t.text || '',
              timestamp: new Date(),
            }));
            
            // Detect speaking based on new messages
            if (newMessages.length > lastMessageCountRef.current) {
              const lastMessage = newMessages[newMessages.length - 1];
              
              // Clear previous timeout
              if (speakingTimeoutRef.current) {
                clearTimeout(speakingTimeoutRef.current);
              }
              
              // Set speaking state based on who sent the last message
              if (lastMessage.role === 'user') {
                setIsUserSpeaking(true);
                setIsAgentSpeaking(false);
              } else {
                setIsAgentSpeaking(true);
                setIsUserSpeaking(false);
              }
              
              // Auto-stop speaking after 2 seconds of no new messages
              speakingTimeoutRef.current = setTimeout(() => {
                setIsUserSpeaking(false);
                setIsAgentSpeaking(false);
              }, 2000);
              
              lastMessageCountRef.current = newMessages.length;
            }
            
            setMessages(newMessages);
            setMetrics(prev => ({ ...prev, turnCount: newMessages.length }));
          }
        }
      } catch (error) {
        console.error('Error fetching transcript:', error);
      }
    };
    
    const interval = setInterval(fetchTranscript, 1000); // Poll faster for better responsiveness
    return () => {
      clearInterval(interval);
      if (speakingTimeoutRef.current) {
        clearTimeout(speakingTimeoutRef.current);
      }
    };
  }, [callId, callStatus]);

  // SSE Event Stream for real-time events
  useEffect(() => {
    if (!callId || callStatus !== 'connected') return;
    
    // Connect to SSE event stream
    const eventSource = new EventSource(`http://localhost:8000/api/v1/events/stream/${callId}`);
    eventSourceRef.current = eventSource;
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.type || 'unknown';
        
        // Skip heartbeat events
        if (eventType === 'heartbeat') return;
        
        // Handle specific events
        switch (eventType) {
          case 'input_audio_buffer.speech_started':
            // Detect interrupt - if agent was speaking, mark last message as interrupted
            setMessages(prev => {
              if (prev.length > 0) {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg.role === 'assistant') {
                  // Mark as interrupted
                  setMetrics(m => ({ ...m, interrupts: m.interrupts + 1 }));
                  return prev.map((msg, i) => 
                    i === prev.length - 1 ? { ...msg, interrupted: true } : msg
                  );
                }
              }
              return prev;
            });
            setIsUserSpeaking(true);
            setIsAgentSpeaking(false);
            break;
            
          case 'input_audio_buffer.speech_stopped':
            setIsUserSpeaking(false);
            break;
            
          case 'response.audio_transcript.delta':
          case 'response.audio_transcript.done':
            setIsAgentSpeaking(true);
            setIsUserSpeaking(false);
            // Auto-stop after a delay
            if (speakingTimeoutRef.current) clearTimeout(speakingTimeoutRef.current);
            speakingTimeoutRef.current = setTimeout(() => setIsAgentSpeaking(false), 1500);
            break;
            
          case 'response.done':
            setIsAgentSpeaking(false);
            // Fetch updated cost
            fetchCost();
            break;
            
          case 'error':
            toast.error(data.error?.message || 'An error occurred');
            break;
        }
      } catch (error) {
        console.error('SSE parse error:', error);
      }
    };
    
    eventSource.onerror = () => {
      console.warn('SSE connection error, will retry...');
    };
    
    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [callId, callStatus]);

  // Fetch cost data
  const fetchCost = async () => {
    if (!callId) return;
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/v1/events/cost/${callId}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.cost) {
          setCost(data.cost);
        }
      }
    } catch (error) {
      console.error('Error fetching cost:', error);
    }
  };

  const handleStartCall = async () => {
    if (!phoneNumber.trim()) {
      toast.error('Please enter a phone number');
      return;
    }
    
    setCallStatus('connecting');
    setMessages([]);
    setMetrics({ duration: 0, latency: 0, interrupts: 0, turnCount: 0 });
    setCost(null);
    setIsUserSpeaking(false);
    setIsAgentSpeaking(false);
    lastMessageCountRef.current = 0;
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/v1/calls/outbound', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          phone_number: phoneNumber,
          agent_id: agentId,
          customer_name: customerName || undefined,
        }),
      });
      
      const result = await response.json();
      
      if (result.success) {
        const newCallId = result.call_id;  // AudioSocket UUID from backend
        const newChannelId = result.channel_id;  // Asterisk channel ID
        if (!newCallId) {
          console.error('Backend did not return call_id (UUID)');
        }
        setCallId(newCallId || `call-${Date.now()}`);
        setChannelId(newChannelId || null);
        setCallStatus('connected');
        toast.success('Call started');
        onCallStart?.(newCallId || '');
      } else {
        throw new Error(result.message || 'Failed to start call');
      }
    } catch (error) {
      console.error('Call error:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to start call');
      setCallStatus('idle');
    }
  };

  const handleEndCall = async () => {
    // Close SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    // Hangup via Asterisk ARI using channel_id
    if (channelId) {
      try {
        const token = localStorage.getItem('access_token');
        await fetch(`http://localhost:8000/api/v1/calls/hangup/${channelId}`, {
          method: 'DELETE',
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });
      } catch (error) {
        console.error('Hangup error:', error);
      }
    }
    
    setCallStatus('ended');
    setCallId(null);
    setChannelId(null);
    setIsUserSpeaking(false);
    setIsAgentSpeaking(false);
    onCallEnd?.();
    toast.info('Call ended');
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

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header with phone input and controls */}
      <div className="p-4 border-b border-border bg-card rounded-t-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">Live Test Console</h3>
          {callStatus === 'connected' && (
            <CallMetricsCompact metrics={metrics} cost={cost} isActive={true} />
          )}
        </div>
        
        <div className="flex gap-3">
          {/* Customer name and Phone input */}
          <div className="flex-1 flex gap-3">
            {/* Customer Name Input */}
            <div className="relative flex-1">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <input
                type="text"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="Customer Name (optional)"
                disabled={callStatus === 'connected'}
                className="w-full pl-10 pr-3 py-2.5 rounded-lg border border-border bg-background 
                         focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 text-sm"
              />
            </div>
            {/* Phone Input */}
            <div className="relative flex-1">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="Phone Number"
                disabled={callStatus === 'connected'}
                className="w-full pl-10 pr-10 py-2.5 rounded-lg border border-border bg-background 
                         focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 text-sm"
              />
              <button
                onClick={handlePastePhone}
                disabled={callStatus === 'connected'}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded hover:bg-muted transition-colors disabled:opacity-50"
                title="Paste"
              >
                <Clipboard className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          </div>
          
          {/* Call controls */}
          <div className="flex gap-2">
            {callStatus === 'idle' || callStatus === 'ended' ? (
              <button
                onClick={handleStartCall}
                disabled={!phoneNumber.trim()}
                className="flex items-center gap-2 px-4 py-2.5 bg-green-500 text-white rounded-lg 
                         hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Phone className="h-4 w-4" />
                Call
              </button>
            ) : callStatus === 'connecting' ? (
              <button disabled className="flex items-center gap-2 px-4 py-2.5 bg-yellow-500 text-white rounded-lg">
                <Loader2 className="h-4 w-4 animate-spin" />
                Connecting...
              </button>
            ) : (
              <>
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={cn(
                    'p-2.5 rounded-lg transition-colors',
                    isMuted ? 'bg-red-500/20 text-red-500' : 'bg-muted hover:bg-muted/80'
                  )}
                  title={isMuted ? 'Unmute' : 'Mute'}
                >
                  {isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                </button>
                <button
                  onClick={() => setIsAudioMuted(!isAudioMuted)}
                  className={cn(
                    'p-2.5 rounded-lg transition-colors',
                    isAudioMuted ? 'bg-red-500/20 text-red-500' : 'bg-muted hover:bg-muted/80'
                  )}
                  title={isAudioMuted ? 'Unmute Audio' : 'Mute Audio'}
                >
                  {isAudioMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                </button>
                <button
                  onClick={handleEndCall}
                  className="flex items-center gap-2 px-4 py-2.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                >
                  <PhoneOff className="h-4 w-4" />
                  Hang Up
                </button>
              </>
            )}
          </div>
        </div>
      </div>
      
      {/* Audio waveform */}
      <AudioWaveform 
        isActive={callStatus === 'connected'}
        isUserSpeaking={isUserSpeaking}
        isAgentSpeaking={isAgentSpeaking}
        className="rounded-none border-x border-border"
      />
    </div>
  );
}
