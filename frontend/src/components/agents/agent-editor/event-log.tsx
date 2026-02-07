'use client';

import { cn } from '@/lib/utils';
import { useState, useRef, useEffect } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Server,
  Smartphone,
  Trash2,
  Copy,
  Check,
  Filter,
} from 'lucide-react';

export interface RealtimeEvent {
  id: string;
  type: string;
  source: 'client' | 'server';
  timestamp: Date;
  data: Record<string, unknown>;
}

interface EventLogProps {
  events: RealtimeEvent[];
  onClear?: () => void;
  maxHeight?: string;
  className?: string;
}

const eventColors: Record<string, string> = {
  // Session events
  'session.created': 'text-green-500',
  'session.update': 'text-blue-500',
  'session.updated': 'text-blue-400',
  
  // Input audio events
  'input_audio_buffer.append': 'text-gray-400',
  'input_audio_buffer.commit': 'text-yellow-500',
  'input_audio_buffer.speech_started': 'text-orange-500',
  'input_audio_buffer.speech_stopped': 'text-orange-400',
  'input_audio_buffer.cleared': 'text-gray-500',
  
  // Conversation events
  'conversation.item.create': 'text-purple-500',
  'conversation.item.created': 'text-purple-400',
  'conversation.item.deleted': 'text-red-400',
  
  // Response events
  'response.create': 'text-cyan-500',
  'response.created': 'text-cyan-400',
  'response.output_item.added': 'text-cyan-300',
  'response.content_part.added': 'text-cyan-200',
  'response.audio.delta': 'text-indigo-400',
  'response.audio_transcript.delta': 'text-indigo-500',
  'response.text.delta': 'text-indigo-600',
  'response.done': 'text-green-400',
  'response.cancel': 'text-red-500',
  
  // Error events
  'error': 'text-red-600',
  
  // Rate limit
  'rate_limits.updated': 'text-amber-500',
};

function EventItem({ event, isExpanded, onToggle }: { 
  event: RealtimeEvent; 
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const colorClass = eventColors[event.type] || 'text-gray-500';
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(event.data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      fractionalSecondDigits: 3 
    });
  };

  return (
    <div className="border-b border-border/50 last:border-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/50 transition-colors text-left"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
        )}
        
        {event.source === 'client' ? (
          <Smartphone className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />
        ) : (
          <Server className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
        )}
        
        <span className={cn('font-mono text-xs flex-1 truncate', colorClass)}>
          {event.type}
        </span>
        
        <span className="text-[10px] text-muted-foreground font-mono">
          {formatTime(event.timestamp)}
        </span>
      </button>
      
      {isExpanded && (
        <div className="px-3 pb-3">
          <div className="relative">
            <button
              onClick={copyToClipboard}
              className="absolute top-2 right-2 p-1 rounded hover:bg-muted transition-colors"
              title="Copy JSON"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5 text-muted-foreground" />
              )}
            </button>
            <pre className="text-[10px] font-mono bg-muted/50 rounded-lg p-3 overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(event.data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export function EventLog({ events, onClear, maxHeight = '400px', className }: EventLogProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<'all' | 'client' | 'server'>('all');
  const [typeFilter, setTypeFilter] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const toggleExpanded = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredEvents = events.filter(event => {
    if (filter !== 'all' && event.source !== filter) return false;
    if (typeFilter && !event.type.toLowerCase().includes(typeFilter.toLowerCase())) return false;
    return true;
  });

  return (
    <div className={cn('flex flex-col rounded-xl border border-border bg-card', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-sm">Event Log</h3>
          <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded-full">
            {filteredEvents.length}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Source filter */}
          <div className="flex items-center gap-1 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={cn(
                'px-2 py-1 rounded transition-colors',
                filter === 'all' ? 'bg-primary-500 text-white' : 'bg-muted hover:bg-muted/80'
              )}
            >
              All
            </button>
            <button
              onClick={() => setFilter('client')}
              className={cn(
                'px-2 py-1 rounded transition-colors flex items-center gap-1',
                filter === 'client' ? 'bg-blue-500 text-white' : 'bg-muted hover:bg-muted/80'
              )}
            >
              <Smartphone className="h-3 w-3" />
            </button>
            <button
              onClick={() => setFilter('server')}
              className={cn(
                'px-2 py-1 rounded transition-colors flex items-center gap-1',
                filter === 'server' ? 'bg-green-500 text-white' : 'bg-muted hover:bg-muted/80'
              )}
            >
              <Server className="h-3 w-3" />
            </button>
          </div>
          
          {/* Type filter */}
          <div className="relative">
            <Filter className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter..."
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-24 pl-7 pr-2 py-1 text-xs rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          
          {/* Clear button */}
          {onClear && (
            <button
              onClick={onClear}
              className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
              title="Clear events"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
      
      {/* Events list */}
      <div 
        ref={scrollRef}
        className="overflow-y-auto"
        style={{ maxHeight }}
        onScroll={(e) => {
          const target = e.target as HTMLDivElement;
          const isAtBottom = target.scrollHeight - target.scrollTop - target.clientHeight < 50;
          setAutoScroll(isAtBottom);
        }}
      >
        {filteredEvents.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
            No events yet
          </div>
        ) : (
          filteredEvents.map(event => (
            <EventItem
              key={event.id}
              event={event}
              isExpanded={expandedIds.has(event.id)}
              onToggle={() => toggleExpanded(event.id)}
            />
          ))
        )}
      </div>
      
      {/* Auto-scroll indicator */}
      {!autoScroll && events.length > 0 && (
        <button
          onClick={() => {
            setAutoScroll(true);
            if (scrollRef.current) {
              scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
            }
          }}
          className="absolute bottom-16 right-4 px-3 py-1 text-xs bg-primary-500 text-white rounded-full shadow-lg hover:bg-primary-600 transition-colors"
        >
          ↓ New events
        </button>
      )}
    </div>
  );
}
