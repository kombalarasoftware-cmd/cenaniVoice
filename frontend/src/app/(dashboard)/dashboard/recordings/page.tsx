'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import {
  FileAudio,
  Play,
  Pause,
  Download,
  Search,
  Filter,
  Calendar,
  Clock,
  User,
  Bot,
  Phone,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronRight,
  Volume2,
} from 'lucide-react';

interface Recording {
  id: string;
  phoneNumber: string;
  customerName: string;
  campaignName: string;
  agentName: string;
  duration: number;
  status: 'completed' | 'transferred' | 'failed' | 'no_answer';
  sentiment: 'positive' | 'neutral' | 'negative';
  createdAt: string;
  fileSize: string;
  hasTranscription: boolean;
}

const mockRecordings: Recording[] = [];

export default function RecordingsPage() {
  const [selectedRecording, setSelectedRecording] = useState<Recording | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackProgress, setPlaybackProgress] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');

  const formatDuration = (seconds: number) => {
    if (seconds === 0) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const statusConfig = {
    completed: { label: 'Completed', color: 'text-success-500', bg: 'bg-success-500/10', icon: CheckCircle },
    transferred: { label: 'Transferred', color: 'text-warning-500', bg: 'bg-warning-500/10', icon: AlertCircle },
    failed: { label: 'Failed', color: 'text-error-500', bg: 'bg-error-500/10', icon: XCircle },
    no_answer: { label: 'No Answer', color: 'text-muted-foreground', bg: 'bg-muted', icon: Phone },
  };

  const sentimentConfig = {
    positive: { label: 'Positive', color: 'text-success-500' },
    neutral: { label: 'Neutral', color: 'text-muted-foreground' },
    negative: { label: 'Negative', color: 'text-error-500' },
  };

  return (
    <div className="min-h-screen">
      <Header
        title="Recordings"
        description="Listen to and analyze call recordings"
      />

      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recordings list */}
          <div className="lg:col-span-2 space-y-4">
            {/* Search and filters */}
            <div className="flex items-center gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search by name, phone, or campaign..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={cn(
                    'w-full pl-9 pr-4 py-2 rounded-lg bg-background border border-border',
                    'focus:border-primary-500 focus:outline-none transition-colors'
                  )}
                />
              </div>
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors">
                <Filter className="h-4 w-4" />
                Filters
              </button>
              <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors">
                <Calendar className="h-4 w-4" />
                Date Range
              </button>
            </div>

            {/* Recordings table */}
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="text-left py-3 px-4 font-medium text-sm">Customer</th>
                      <th className="text-left py-3 px-4 font-medium text-sm">Campaign</th>
                      <th className="text-left py-3 px-4 font-medium text-sm">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-sm">Duration</th>
                      <th className="text-left py-3 px-4 font-medium text-sm">Date</th>
                      <th className="text-right py-3 px-4 font-medium text-sm">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockRecordings.map((recording) => {
                      const StatusIcon = statusConfig[recording.status].icon;
                      return (
                        <tr
                          key={recording.id}
                          onClick={() => setSelectedRecording(recording)}
                          className={cn(
                            'border-b border-border cursor-pointer transition-colors',
                            selectedRecording?.id === recording.id
                              ? 'bg-primary-500/5'
                              : 'hover:bg-muted/50'
                          )}
                        >
                          <td className="py-3 px-4">
                            <div>
                              <p className="font-medium">{recording.customerName}</p>
                              <p className="text-sm text-muted-foreground">
                                {recording.phoneNumber}
                              </p>
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <p className="text-sm">{recording.campaignName}</p>
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={cn(
                                'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
                                statusConfig[recording.status].bg,
                                statusConfig[recording.status].color
                              )}
                            >
                              <StatusIcon className="h-3 w-3" />
                              {statusConfig[recording.status].label}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="font-mono text-sm">
                              {formatDuration(recording.duration)}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className="text-sm text-muted-foreground">
                              {recording.createdAt}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              {recording.duration > 0 && (
                                <>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedRecording(recording);
                                      setIsPlaying(true);
                                    }}
                                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-500/10 hover:bg-primary-500/20 text-primary-500 transition-colors"
                                  >
                                    <Play className="h-4 w-4" />
                                  </button>
                                  <button
                                    onClick={(e) => e.stopPropagation()}
                                    className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted transition-colors"
                                  >
                                    <Download className="h-4 w-4 text-muted-foreground" />
                                  </button>
                                </>
                              )}
                              <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Recording detail / Player */}
          <div className="lg:col-span-1">
            {selectedRecording ? (
              <div className="sticky top-24 space-y-4">
                {/* Player */}
                <div className="p-6 rounded-xl bg-card border border-border">
                  <div className="text-center mb-6">
                    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary-500/20 to-secondary-500/20 mx-auto mb-4">
                      {isPlaying ? (
                        <Volume2 className="h-10 w-10 text-primary-500 animate-pulse" />
                      ) : (
                        <FileAudio className="h-10 w-10 text-primary-500" />
                      )}
                    </div>
                    <h3 className="font-semibold">{selectedRecording.customerName}</h3>
                    <p className="text-sm text-muted-foreground">
                      {selectedRecording.phoneNumber}
                    </p>
                  </div>

                  {/* Waveform placeholder */}
                  <div className="h-16 bg-muted/30 rounded-lg mb-4 flex items-center justify-center gap-1 px-4">
                    {Array.from({ length: 40 }).map((_, i) => (
                      <div
                        key={i}
                        className={cn(
                          'w-1 rounded-full transition-all duration-150',
                          isPlaying ? 'bg-primary-500' : 'bg-muted-foreground/30'
                        )}
                        style={{
                          height: `${Math.random() * 100}%`,
                          opacity: i / 40 < playbackProgress ? 1 : 0.3,
                        }}
                      />
                    ))}
                  </div>

                  {/* Progress */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground mb-4">
                    <span>0:00</span>
                    <span>{formatDuration(selectedRecording.duration)}</span>
                  </div>

                  {/* Controls */}
                  <div className="flex items-center justify-center gap-4">
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className={cn(
                        'flex h-14 w-14 items-center justify-center rounded-full',
                        'bg-primary-500 hover:bg-primary-600 text-white transition-colors'
                      )}
                    >
                      {isPlaying ? (
                        <Pause className="h-7 w-7" />
                      ) : (
                        <Play className="h-7 w-7 ml-1" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Details */}
                <div className="p-4 rounded-xl bg-card border border-border space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Campaign</span>
                    <span className="text-sm font-medium">{selectedRecording.campaignName}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Agent</span>
                    <span className="text-sm font-medium">{selectedRecording.agentName}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Sentiment</span>
                    <span className={cn('text-sm font-medium', sentimentConfig[selectedRecording.sentiment].color)}>
                      {sentimentConfig[selectedRecording.sentiment].label}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">File Size</span>
                    <span className="text-sm font-medium">{selectedRecording.fileSize}</span>
                  </div>
                </div>

                {/* Transcription */}
                {selectedRecording.hasTranscription && (
                  <div className="p-4 rounded-xl bg-card border border-border">
                    <h4 className="font-medium mb-3">Transcription</h4>
                    <div className="space-y-3 max-h-64 overflow-auto custom-scrollbar">
                      <div className="flex gap-3">
                        <Bot className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
                        <div className="text-sm">
                          <span className="font-medium">AI:</span>{' '}
                          <span className="text-muted-foreground">
                            Merhaba {selectedRecording.customerName} Bey/Hanım, ben XYZ şirketinden arıyorum...
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <User className="h-5 w-5 text-secondary-500 flex-shrink-0 mt-0.5" />
                        <div className="text-sm">
                          <span className="font-medium">Customer:</span>{' '}
                          <span className="text-muted-foreground">
                            Evet, buyurun...
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <Bot className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
                        <div className="text-sm">
                          <span className="font-medium">AI:</span>{' '}
                          <span className="text-muted-foreground">
                            Ödemeniz hakkında bilgi vermek için arıyorum...
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 rounded-xl bg-card border border-border text-center">
                <FileAudio className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-medium mb-2">Select a Recording</h3>
                <p className="text-sm text-muted-foreground">
                  Click on a recording to view details and listen
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
