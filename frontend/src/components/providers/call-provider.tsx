'use client';

import { createContext, useContext, useState, useRef, useEffect, useCallback, useMemo, type ReactNode } from 'react';
import { toast } from 'sonner';

// ============================================================================
// Types
// ============================================================================

export interface CallMetrics {
  duration: number;
  latency: number;
  interrupts: number;
  turnCount: number;
}

export interface CostBreakdown {
  input_tokens: { text: number; audio: number; total: number };
  output_tokens: { text: number; audio: number; total: number };
  cost: {
    input_text?: number;
    input_audio?: number;
    output_text?: number;
    output_audio?: number;
    total: number;
  };
  model?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  interrupted?: boolean;
}

export type CallStatus = 'idle' | 'connecting' | 'connected' | 'ended';

interface StartCallParams {
  phoneNumber: string;
  agentId: string;
  customerName?: string;
  customerTitle?: '' | 'Mr' | 'Mrs';
}

interface CallContextValue {
  // Call identity
  callStatus: CallStatus;
  callId: string | null;
  channelId: string | null;
  agentId: string | null;

  // Call info
  phoneNumber: string;
  setPhoneNumber: (v: string) => void;
  customerName: string;
  setCustomerName: (v: string) => void;
  customerTitle: '' | 'Mr' | 'Mrs';
  setCustomerTitle: (v: '' | 'Mr' | 'Mrs') => void;

  // Audio controls
  isMuted: boolean;
  setIsMuted: (v: boolean) => void;
  isAudioMuted: boolean;
  setIsAudioMuted: (v: boolean) => void;

  // Live data
  messages: Message[];
  metrics: CallMetrics;
  cost: CostBreakdown | null;
  isUserSpeaking: boolean;
  isAgentSpeaking: boolean;

  // Actions
  startCall: (params: StartCallParams) => Promise<void>;
  endCall: () => Promise<void>;
  resetCall: () => void;
}

// ============================================================================
// Context
// ============================================================================

const CallContext = createContext<CallContextValue | null>(null);

export function useCall(): CallContextValue {
  const ctx = useContext(CallContext);
  if (!ctx) {
    throw new Error('useCall must be used within a CallProvider');
  }
  return ctx;
}

// ============================================================================
// Provider
// ============================================================================

export function CallProvider({ children }: { children: ReactNode }) {
  // Call identity
  const [callStatus, setCallStatus] = useState<CallStatus>('idle');
  const [callId, setCallId] = useState<string | null>(null);
  const [channelId, setChannelId] = useState<string | null>(null);
  const [agentId, setAgentId] = useState<string | null>(null);

  // Call info
  const [phoneNumber, setPhoneNumber] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [customerTitle, setCustomerTitle] = useState<'' | 'Mr' | 'Mrs'>('');

  // Audio controls
  const [isMuted, setIsMuted] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);

  // Live data
  const [messages, setMessages] = useState<Message[]>([]);
  const [metrics, setMetrics] = useState<CallMetrics>({
    duration: 0,
    latency: 0,
    interrupts: 0,
    turnCount: 0,
  });
  const [cost, setCost] = useState<CostBreakdown | null>(null);

  // Speaking indicators
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);

  // Refs (survive re-renders, managed internally)
  const durationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const transcriptIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speakingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastMessageCountRef = useRef(0);
  const callIdRef = useRef<string | null>(null);

  // Keep callIdRef in sync
  useEffect(() => {
    callIdRef.current = callId;
  }, [callId]);

  // --------------------------------------------------
  // Duration timer
  // --------------------------------------------------
  useEffect(() => {
    if (callStatus === 'connected') {
      durationIntervalRef.current = setInterval(() => {
        setMetrics(prev => ({ ...prev, duration: prev.duration + 1 }));
      }, 1000);
    }
    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
    };
  }, [callStatus]);

  // --------------------------------------------------
  // Fetch cost
  // --------------------------------------------------
  const fetchCost = useCallback(async () => {
    const id = callIdRef.current;
    if (!id) return;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8000/api/v1/events/cost/${id}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
      if (response.ok) {
        const data = await response.json();
        if (data.cost) setCost(data.cost);
      }
    } catch (error) {
      console.error('Error fetching cost:', error);
    }
  }, []);

  // --------------------------------------------------
  // SSE EventSource
  // --------------------------------------------------
  useEffect(() => {
    if (!callId || callStatus !== 'connected') return;

    const eventSource = new EventSource(`http://localhost:8000/api/v1/events/stream/${callId}`);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const eventType = data.type || 'unknown';
        if (eventType === 'heartbeat') return;

        switch (eventType) {
          case 'input_audio_buffer.speech_started':
            setMessages(prev => {
              if (prev.length > 0) {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg.role === 'assistant') {
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
            if (speakingTimeoutRef.current) clearTimeout(speakingTimeoutRef.current);
            speakingTimeoutRef.current = setTimeout(() => setIsAgentSpeaking(false), 1500);
            break;

          case 'response.done':
            setIsAgentSpeaking(false);
            fetchCost();
            break;

          case 'error': {
            const errMsg = data.error?.message || '';
            const benign = ['no active response', 'cancellation failed'];
            if (!benign.some(b => errMsg.toLowerCase().includes(b))) {
              toast.error(errMsg || 'An error occurred');
            }
            break;
          }
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
  }, [callId, callStatus, fetchCost]);

  // --------------------------------------------------
  // Transcript polling
  // --------------------------------------------------
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
            const newMessages: Message[] = data.transcript.map(
              (t: { role: string; text?: string; content?: string }, i: number) => ({
                id: `${callId}-${i}`,
                role: (t.role === 'agent' || t.role === 'assistant') ? 'assistant' as const : 'user' as const,
                content: t.content || t.text || '',
                timestamp: new Date(),
              })
            );

            // Detect speaking based on new messages
            if (newMessages.length > lastMessageCountRef.current) {
              const lastMessage = newMessages[newMessages.length - 1];
              if (speakingTimeoutRef.current) clearTimeout(speakingTimeoutRef.current);

              if (lastMessage.role === 'user') {
                setIsUserSpeaking(true);
                setIsAgentSpeaking(false);
              } else {
                setIsAgentSpeaking(true);
                setIsUserSpeaking(false);
              }

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

    transcriptIntervalRef.current = setInterval(fetchTranscript, 1000);

    return () => {
      if (transcriptIntervalRef.current) {
        clearInterval(transcriptIntervalRef.current);
        transcriptIntervalRef.current = null;
      }
      if (speakingTimeoutRef.current) {
        clearTimeout(speakingTimeoutRef.current);
      }
    };
  }, [callId, callStatus]);

  // --------------------------------------------------
  // Actions
  // --------------------------------------------------
  const startCall = useCallback(async (params: StartCallParams) => {
    if (!params.phoneNumber.trim()) {
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
    setAgentId(params.agentId);
    setPhoneNumber(params.phoneNumber);
    if (params.customerName !== undefined) setCustomerName(params.customerName);
    if (params.customerTitle !== undefined) setCustomerTitle(params.customerTitle);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8000/api/v1/calls/outbound', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          phone_number: params.phoneNumber,
          agent_id: params.agentId,
          customer_name: params.customerName || undefined,
          customer_title: params.customerTitle || undefined,
        }),
      });

      const result = await response.json();

      if (result.success) {
        const newCallId = result.call_id;
        const newChannelId = result.channel_id;
        setCallId(newCallId || `call-${Date.now()}`);
        setChannelId(newChannelId || null);
        setCallStatus('connected');
        toast.success('Call started');
      } else {
        throw new Error(result.message || 'Failed to start call');
      }
    } catch (error) {
      console.error('Call error:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to start call');
      setCallStatus('idle');
    }
  }, []);

  const endCall = useCallback(async () => {
    // Close SSE
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Stop transcript polling
    if (transcriptIntervalRef.current) {
      clearInterval(transcriptIntervalRef.current);
      transcriptIntervalRef.current = null;
    }

    // Hangup via ARI + Redis signal
    const hangupChannelId = channelId;
    const hangupCallId = callId;

    if (hangupChannelId || hangupCallId) {
      try {
        const token = localStorage.getItem('access_token');
        const params = new URLSearchParams();
        if (hangupCallId) params.set('call_id', hangupCallId);
        const url = hangupChannelId
          ? `http://localhost:8000/api/v1/calls/hangup/${hangupChannelId}?${params}`
          : `http://localhost:8000/api/v1/calls/hangup/_none?${params}`;
        await fetch(url, {
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
    toast.info('Call ended');
  }, [callId, channelId]);

  const resetCall = useCallback(() => {
    setCallStatus('idle');
    setMessages([]);
    setMetrics({ duration: 0, latency: 0, interrupts: 0, turnCount: 0 });
    setCost(null);
    setCustomerTitle('');
    setAgentId(null);
    lastMessageCountRef.current = 0;
  }, []);

  // --------------------------------------------------
  // Context value
  // --------------------------------------------------
  const value = useMemo<CallContextValue>(() => ({
    callStatus,
    callId,
    channelId,
    agentId,
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
  }), [
    callStatus, callId, channelId, agentId,
    phoneNumber, customerName, customerTitle,
    isMuted, isAudioMuted,
    messages, metrics, cost,
    isUserSpeaking, isAgentSpeaking,
    startCall, endCall, resetCall,
  ]);

  return (
    <CallContext.Provider value={value}>
      {children}
    </CallContext.Provider>
  );
}
