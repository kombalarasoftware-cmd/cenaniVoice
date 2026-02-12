'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { cn, formatDuration } from '@/lib/utils';
import {
  ArrowLeft,
  Bot,
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Loader2,
  AlertCircle,
  MessageSquare,
} from 'lucide-react';

interface AgentInfo {
  id: number;
  name: string;
  description: string;
  language: string;
  voice: string;
  status: string;
}

interface TranscriptEntry {
  role: 'agent' | 'user' | 'system';
  text: string;
  timestamp: string;
}

export default function AgentTestPage() {
  const params = useParams();
  const agentId = params.id as string;

  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Call state
  const [isCallActive, setIsCallActive] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeakerOn, setIsSpeakerOn] = useState(true);
  const [callDuration, setCallDuration] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [testPhone, setTestPhone] = useState('');
  const [activeCallId, setActiveCallId] = useState<number | null>(null);

  const fetchAgent = useCallback(async () => {
    try {
      setError('');
      const data = await api.get<AgentInfo>(`/agents/${agentId}`);
      setAgent(data);
    } catch (err) {
      console.error('Failed to fetch agent:', err);
      setError(err instanceof Error ? err.message : 'Failed to load agent');
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    fetchAgent();
  }, [fetchAgent]);

  // Call duration timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isCallActive) {
      interval = setInterval(() => {
        setCallDuration((d) => d + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isCallActive]);

  const handleStartCall = async () => {
    if (!testPhone) {
      toast.error('Please enter a phone number');
      return;
    }

    setIsConnecting(true);
    setTranscript([]);
    setCallDuration(0);

    try {
      const result = await api.post<{
        success: boolean;
        call_id: string | null;
        db_call_id: number | null;
        channel_id: string | null;
        message: string;
      }>('/calls/outbound', {
        phone_number: testPhone.replace(/[\s\-\(\)\+]/g, ''),
        agent_id: agentId,
      });
      if (!result.success) {
        throw new Error(result.message || 'Failed to start call');
      }
      setActiveCallId(result.db_call_id);
      setIsCallActive(true);
      setTranscript([{
        role: 'system',
        text: 'Call initiated — ringing...',
        timestamp: new Date().toLocaleTimeString('en-US'),
      }]);
      toast.success('Test call started');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to start test call');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleEndCall = async () => {
    try {
      if (activeCallId) {
        await api.post(`/calls/${activeCallId}/hangup`);
      }
    } catch (err) {
      console.error('Failed to end call:', err);
    }
    setIsCallActive(false);
    setActiveCallId(null);
    setTranscript((prev) => [
      ...prev,
      {
        role: 'system',
        text: 'Call ended',
        timestamp: new Date().toLocaleTimeString('en-US'),
      },
    ]);
    toast.info('Test call ended');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="p-6">
        <Link href={`/dashboard/agents/${agentId}`} className="flex items-center gap-2 text-muted-foreground hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4" />
          Back to Agent
        </Link>
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-error-500 mx-auto mb-4" />
          <p className="text-error-500 mb-4">{error || 'Agent not found'}</p>
          <button
            onClick={fetchAgent}
            className="px-4 py-2 rounded-lg bg-primary-500 hover:bg-primary-600 text-white font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b border-border bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href={`/dashboard/agents/${agentId}`} className="p-2 rounded-lg hover:bg-muted transition-colors">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary-500/20 to-secondary-500/20">
                <Bot className="h-5 w-5 text-primary-500" />
              </div>
              <div>
                <h1 className="text-lg font-semibold">Test: {agent.name}</h1>
                <p className="text-xs text-muted-foreground">
                  {agent.language} / {agent.voice}
                </p>
              </div>
            </div>
          </div>

          {isCallActive && (
            <div className="flex items-center gap-2 text-sm">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success-500" />
              </span>
              <span className="font-mono font-medium">{formatDuration(callDuration)}</span>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Phone input + controls */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <h2 className="text-sm font-medium text-muted-foreground mb-4">Test Call</h2>

          <div className="flex items-center gap-3">
            <input
              type="tel"
              value={testPhone}
              onChange={(e) => setTestPhone(e.target.value)}
              placeholder="+1 (555) 000-0000"
              disabled={isCallActive || isConnecting}
              className="flex-1 px-4 py-3 bg-muted/30 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
            />

            {!isCallActive ? (
              <button
                onClick={handleStartCall}
                disabled={isConnecting || !testPhone}
                className={cn(
                  'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors',
                  'bg-success-500 hover:bg-success-600 text-white',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isConnecting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Phone className="h-5 w-5" />
                )}
                {isConnecting ? 'Connecting...' : 'Call'}
              </button>
            ) : (
              <button
                onClick={handleEndCall}
                className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium bg-error-500 hover:bg-error-600 text-white transition-colors"
              >
                <PhoneOff className="h-5 w-5" />
                End
              </button>
            )}
          </div>

          {/* Call controls */}
          {isCallActive && (
            <div className="flex items-center gap-3 mt-4 pt-4 border-t border-border">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  isMuted
                    ? 'bg-error-500/10 text-error-500'
                    : 'bg-muted hover:bg-muted/80 text-foreground'
                )}
              >
                {isMuted ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                {isMuted ? 'Unmute' : 'Mute'}
              </button>
              <button
                onClick={() => setIsSpeakerOn(!isSpeakerOn)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  !isSpeakerOn
                    ? 'bg-error-500/10 text-error-500'
                    : 'bg-muted hover:bg-muted/80 text-foreground'
                )}
              >
                {isSpeakerOn ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                {isSpeakerOn ? 'Speaker On' : 'Speaker Off'}
              </button>
            </div>
          )}
        </div>

        {/* Transcript */}
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-medium text-muted-foreground">Live Transcript</h2>
          </div>

          {transcript.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Start a test call to see the transcript</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {transcript.map((entry, index) => (
                <div
                  key={index}
                  className={cn(
                    'flex gap-3 text-sm',
                    entry.role === 'system' && 'justify-center'
                  )}
                >
                  {entry.role === 'system' ? (
                    <span className="text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
                      {entry.text} - {entry.timestamp}
                    </span>
                  ) : (
                    <>
                      <div className={cn(
                        'flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium shrink-0',
                        entry.role === 'agent'
                          ? 'bg-primary-500/10 text-primary-500'
                          : 'bg-secondary-500/10 text-secondary-500'
                      )}>
                        {entry.role === 'agent' ? 'AI' : 'U'}
                      </div>
                      <div className="flex-1">
                        <p className="text-xs text-muted-foreground mb-0.5">
                          {entry.role === 'agent' ? agent.name : 'You'} - {entry.timestamp}
                        </p>
                        <p>{entry.text}</p>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
