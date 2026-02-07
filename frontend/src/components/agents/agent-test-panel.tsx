'use client';

import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  MessageSquare,
  Mic,
  Phone,
  Send,
  Play,
  Square,
  Volume2,
  PhoneCall,
  User,
  Bot,
} from 'lucide-react';
import { VoiceVisualizer, MicButton, AIThinkingDots } from '@/components/ui/voice-visualizer';

type TestMode = 'chat' | 'voice' | 'phone';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const mockConversation: Message[] = [
  {
    id: '1',
    role: 'assistant',
    content: 'Hello, I\'m your VoiceAI assistant. How can I help you?',
    timestamp: new Date(),
  },
];

export function AgentTestPanel() {
  const [mode, setMode] = useState<TestMode>('chat');
  const [messages, setMessages] = useState<Message[]>(mockConversation);
  const [inputValue, setInputValue] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isAIThinking, setIsAIThinking] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [callStatus, setCallStatus] = useState<'idle' | 'calling' | 'connected' | 'ended'>('idle');

  const modes = [
    { id: 'chat' as TestMode, label: 'Chat', icon: MessageSquare },
    { id: 'voice' as TestMode, label: 'Voice Widget', icon: Mic },
    { id: 'phone' as TestMode, label: 'Phone Test', icon: Phone },
  ];

  const sendMessage = () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsAIThinking(true);

    // Simulate AI response
    setTimeout(() => {
      setIsAIThinking(false);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'This is a test response. In real integration, OpenAI Realtime API will be used.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 1500);
  };

  const toggleRecording = () => {
    if (isRecording) {
      setIsRecording(false);
      setAudioLevel(0);
    } else {
      setIsRecording(true);
      // Simulate audio level changes
      const interval = setInterval(() => {
        setAudioLevel(Math.random());
      }, 100);
      setTimeout(() => {
        clearInterval(interval);
        setIsRecording(false);
        setAudioLevel(0);
        // Simulate AI response
        setIsAIThinking(true);
        setTimeout(() => {
          setIsAIThinking(false);
          setIsAISpeaking(true);
          setTimeout(() => setIsAISpeaking(false), 3000);
        }, 1000);
      }, 3000);
    }
  };

  const startPhoneCall = () => {
    if (!phoneNumber.trim()) return;
    setCallStatus('calling');
    // Simulate connection
    setTimeout(() => setCallStatus('connected'), 2000);
  };

  const endPhoneCall = () => {
    setCallStatus('ended');
    setTimeout(() => setCallStatus('idle'), 1000);
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Mode selector */}
      <div className="flex items-center justify-center gap-2 p-1 rounded-xl bg-muted mb-6 w-fit mx-auto">
        {modes.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
              mode === m.id
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <m.icon className="h-4 w-4" />
            {m.label}
          </button>
        ))}
      </div>

      {/* Chat Mode */}
      {mode === 'chat' && (
        <div className="rounded-2xl border border-border bg-card overflow-hidden">
          {/* Messages */}
          <div className="h-[500px] overflow-auto custom-scrollbar p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'flex items-start gap-3',
                  message.role === 'user' && 'flex-row-reverse'
                )}
              >
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full flex-shrink-0',
                    message.role === 'user'
                      ? 'bg-primary-500'
                      : 'bg-gradient-to-br from-primary-500/20 to-secondary-500/20'
                  )}
                >
                  {message.role === 'user' ? (
                    <User className="h-4 w-4 text-white" />
                  ) : (
                    <Bot className="h-4 w-4 text-primary-500" />
                  )}
                </div>
                <div
                  className={cn(
                    'max-w-[70%] px-4 py-2.5 rounded-2xl',
                    message.role === 'user'
                      ? 'bg-primary-500 text-white rounded-tr-sm'
                      : 'bg-muted rounded-tl-sm'
                  )}
                >
                  <p className="text-sm">{message.content}</p>
                </div>
              </div>
            ))}

            {isAIThinking && (
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary-500/20 to-secondary-500/20">
                  <Bot className="h-4 w-4 text-primary-500" />
                </div>
                <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-muted">
                  <AIThinkingDots />
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-border p-4">
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Type a message..."
                className={cn(
                  'flex-1 px-4 py-2.5 rounded-lg bg-background border border-border',
                  'focus:border-primary-500 focus:outline-none transition-colors'
                )}
              />
              <button
                onClick={sendMessage}
                disabled={!inputValue.trim()}
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-lg transition-colors',
                  inputValue.trim()
                    ? 'bg-primary-500 hover:bg-primary-600 text-white'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice Widget Mode */}
      {mode === 'voice' && (
        <div className="rounded-2xl border border-border bg-card p-8">
          <div className="text-center space-y-8">
            {/* Voice visualizer */}
            <div className="relative mx-auto w-64 h-64">
              <VoiceVisualizer
                mode="circular"
                isActive={isRecording || isAISpeaking}
                audioLevel={audioLevel}
                size="lg"
                className="w-full h-full"
              />
              
              {/* Center content */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                {isAIThinking ? (
                  <AIThinkingDots size="lg" />
                ) : isAISpeaking ? (
                  <div className="text-center">
                    <Volume2 className="h-8 w-8 text-primary-500 mx-auto mb-2 animate-pulse" />
                    <p className="text-sm text-muted-foreground">AI Speaking...</p>
                  </div>
                ) : isRecording ? (
                  <div className="text-center">
                    <Mic className="h-8 w-8 text-error-500 mx-auto mb-2 animate-pulse" />
                    <p className="text-sm text-muted-foreground">Listening...</p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Click to speak
                  </p>
                )}
              </div>
            </div>

            {/* Mic button */}
            <MicButton
              isRecording={isRecording}
              onClick={toggleRecording}
              size="lg"
            />

            {/* Instructions */}
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Hold the button and speak to test the voice agent. 
              The AI will respond using the configured voice and language.
            </p>
          </div>
        </div>
      )}

      {/* Phone Test Mode */}
      {mode === 'phone' && (
        <div className="rounded-2xl border border-border bg-card p-8">
          <div className="max-w-md mx-auto space-y-6">
            {callStatus === 'idle' && (
              <>
                <div className="text-center mb-8">
                  <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary-500/20 to-secondary-500/20 mx-auto mb-4">
                    <Phone className="h-10 w-10 text-primary-500" />
                  </div>
                  <h3 className="text-lg font-semibold">Phone Test</h3>
                  <p className="text-sm text-muted-foreground">
                    Enter a phone number to test the agent with a real call
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="+90 5XX XXX XX XX"
                    className={cn(
                      'w-full px-4 py-3 rounded-lg bg-background border border-border',
                      'focus:border-primary-500 focus:outline-none transition-colors',
                      'text-lg text-center font-mono'
                    )}
                  />
                </div>

                <button
                  onClick={startPhoneCall}
                  disabled={!phoneNumber.trim()}
                  className={cn(
                    'w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-colors',
                    phoneNumber.trim()
                      ? 'bg-success-500 hover:bg-success-600 text-white'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
                  <Phone className="h-5 w-5" />
                  Start Test Call
                </button>

                <p className="text-xs text-muted-foreground text-center">
                  Note: Test calls are limited to 2 minutes and will be recorded for analysis.
                </p>
              </>
            )}

            {callStatus === 'calling' && (
              <div className="text-center py-8">
                <div className="flex h-24 w-24 items-center justify-center rounded-full bg-warning-500/10 mx-auto mb-6 animate-pulse">
                  <PhoneCall className="h-12 w-12 text-warning-500 animate-bounce" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Calling...</h3>
                <p className="text-muted-foreground">{phoneNumber}</p>
              </div>
            )}

            {callStatus === 'connected' && (
              <div className="text-center py-8">
                <div className="relative mx-auto w-48 h-48 mb-6">
                  <VoiceVisualizer
                    mode="circular"
                    isActive={true}
                    audioLevel={0.5}
                    size="lg"
                    className="w-full h-full"
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <p className="text-2xl font-mono font-bold text-success-500">
                        00:45
                      </p>
                      <p className="text-sm text-muted-foreground">Connected</p>
                    </div>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground mb-6">{phoneNumber}</p>

                <button
                  onClick={endPhoneCall}
                  className="flex items-center justify-center gap-2 px-8 py-3 rounded-full bg-error-500 hover:bg-error-600 text-white font-medium transition-colors mx-auto"
                >
                  <Square className="h-5 w-5" />
                  End Call
                </button>
              </div>
            )}

            {callStatus === 'ended' && (
              <div className="text-center py-8">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted mx-auto mb-4">
                  <Phone className="h-10 w-10 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Call Ended</h3>
                <p className="text-sm text-muted-foreground">
                  Call recording and transcription will be available shortly.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
