'use client';

import { cn } from '@/lib/utils';
import {
  User, Phone, Mail, MapPin, Clock, Tag,
  ThumbsUp, ThumbsDown, Minus, MessageSquare,
  ArrowRight, AlertCircle, Calendar, Star,
  Activity, TrendingUp, TrendingDown,
} from 'lucide-react';
import { useState, useEffect } from 'react';

interface CallHistory {
  id: string;
  date: string;
  duration: number;
  outcome: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  summary: string;
  tags: string[];
}

interface CustomerProfile {
  name: string;
  phone: string;
  email: string;
  address: string;
  totalCalls: number;
  lastCallDate: string;
  averageSentiment: 'positive' | 'neutral' | 'negative';
  tags: string[];
  callHistory: CallHistory[];
  qualityScore: number;
  conversationPhase: 'opening' | 'gathering' | 'resolution' | 'closing';
  currentSentiment: 'positive' | 'neutral' | 'negative';
  turnCount: number;
}

// Phase display config
const phaseConfig = {
  opening: { label: 'Opening', color: 'bg-blue-500/10 text-blue-500', icon: MessageSquare },
  gathering: { label: 'Gathering Info', color: 'bg-amber-500/10 text-amber-500', icon: Activity },
  resolution: { label: 'Issue Resolution', color: 'bg-red-500/10 text-red-500', icon: AlertCircle },
  closing: { label: 'Closing', color: 'bg-green-500/10 text-green-500', icon: Star },
};

const sentimentConfig = {
  positive: { icon: ThumbsUp, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Positive' },
  neutral: { icon: Minus, color: 'text-gray-500', bg: 'bg-gray-500/10', label: 'Neutral' },
  negative: { icon: ThumbsDown, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Negative' },
};

// Mock data - in production would come from API/SSE
const mockProfile: CustomerProfile = {
  name: 'John Smith',
  phone: '+90 532 XXX XX 12',
  email: 'ahmet@example.com',
  address: 'Kadıköy, İstanbul',
  totalCalls: 3,
  lastCallDate: '2026-02-05',
  averageSentiment: 'neutral',
  tags: ['interested', 'callback'],
  qualityScore: 78,
  conversationPhase: 'gathering',
  currentSentiment: 'positive',
  turnCount: 5,
  callHistory: [
    {
      id: '1',
      date: '2026-02-05 14:30',
      duration: 180,
      outcome: 'callback',
      sentiment: 'neutral',
      summary: 'Customer requested invoice info, callback scheduled.',
      tags: ['info_request', 'callback'],
    },
    {
      id: '2',
      date: '2026-02-01 10:15',
      duration: 120,
      outcome: 'completed',
      sentiment: 'positive',
      summary: 'Contact information updated.',
      tags: ['info_update'],
    },
  ],
};

function formatDuration(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

export function CustomerProfileCard() {
  const [profile, setProfile] = useState<CustomerProfile>(mockProfile);
  const [isExpanded, setIsExpanded] = useState(false);

  // Simulate real-time phase updates
  useEffect(() => {
    const phases: CustomerProfile['conversationPhase'][] = ['opening', 'gathering', 'resolution', 'closing'];
    let idx = phases.indexOf(profile.conversationPhase);
    
    const interval = setInterval(() => {
      setProfile((prev) => ({
        ...prev,
        turnCount: prev.turnCount + 1,
      }));
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  const phase = phaseConfig[profile.conversationPhase];
  const PhaseIcon = phase.icon;
  const sentiment = sentimentConfig[profile.currentSentiment];
  const SentimentIcon = sentiment.icon;

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/10">
            <User className="h-5 w-5 text-primary-500" />
          </div>
          <div>
            <h3 className="font-semibold">Customer Profile</h3>
            <p className="text-sm text-muted-foreground">
              Real-time call context
            </p>
          </div>
        </div>
        {/* Quality Score Badge */}
        <div className={cn(
          'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold',
          profile.qualityScore >= 80 ? 'bg-green-500/10 text-green-500' :
          profile.qualityScore >= 50 ? 'bg-amber-500/10 text-amber-500' :
          'bg-red-500/10 text-red-500'
        )}>
          <Star className="h-3.5 w-3.5" />
          {profile.qualityScore}/100
        </div>
      </div>

      {/* Customer Info */}
      <div className="space-y-2 mb-4 p-3 rounded-xl bg-muted/50">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{profile.name || 'Unknown'}</span>
        </div>
        {profile.phone && (
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{profile.phone}</span>
          </div>
        )}
        {profile.email && (
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{profile.email}</span>
          </div>
        )}
        {profile.address && (
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{profile.address}</span>
          </div>
        )}
      </div>

      {/* Live Status Row */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {/* Conversation Phase */}
        <div className={cn('flex flex-col items-center p-2 rounded-lg', phase.color)}>
          <PhaseIcon className="h-4 w-4 mb-1" />
          <span className="text-xs font-medium">{phase.label}</span>
        </div>
        {/* Current Sentiment */}
        <div className={cn('flex flex-col items-center p-2 rounded-lg', sentiment.bg)}>
          <SentimentIcon className={cn('h-4 w-4 mb-1', sentiment.color)} />
          <span className={cn('text-xs font-medium', sentiment.color)}>{sentiment.label}</span>
        </div>
        {/* Turn Count */}
        <div className="flex flex-col items-center p-2 rounded-lg bg-purple-500/10">
          <MessageSquare className="h-4 w-4 mb-1 text-purple-500" />
          <span className="text-xs font-medium text-purple-500">{profile.turnCount} turns</span>
        </div>
      </div>

      {/* Tags */}
      {profile.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {profile.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground"
            >
              <Tag className="h-3 w-3" />
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Call History Stats */}
      <div className="flex items-center justify-between text-sm mb-3">
        <span className="text-muted-foreground">
          <Clock className="h-3.5 w-3.5 inline mr-1" />
          {profile.totalCalls} previous calls
        </span>
        <span className="text-muted-foreground">
          Last: {profile.lastCallDate}
        </span>
      </div>

      {/* Expandable Call History */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-sm text-primary-500 hover:text-primary-600 font-medium flex items-center justify-center gap-1"
      >
        {isExpanded ? 'Hide' : 'Call History'}
        <ArrowRight className={cn('h-3.5 w-3.5 transition-transform', isExpanded && 'rotate-90')} />
      </button>

      {isExpanded && (
        <div className="mt-3 space-y-2">
          {profile.callHistory.map((call) => {
            const callSentiment = sentimentConfig[call.sentiment];
            const CallSentimentIcon = callSentiment.icon;
            return (
              <div key={call.id} className="p-3 rounded-lg border border-border bg-background">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-muted-foreground">{call.date}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs">{formatDuration(call.duration)}</span>
                    <CallSentimentIcon className={cn('h-3.5 w-3.5', callSentiment.color)} />
                  </div>
                </div>
                <p className="text-sm mb-1">{call.summary}</p>
                <div className="flex flex-wrap gap-1">
                  {call.tags.map((tag) => (
                    <span key={tag} className="px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
