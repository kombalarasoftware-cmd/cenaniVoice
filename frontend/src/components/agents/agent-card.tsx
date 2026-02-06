'use client';

import { cn } from '@/lib/utils';
import Link from 'next/link';
import {
  Bot,
  MoreVertical,
  Play,
  Pause,
  Copy,
  Trash2,
  Edit,
  BarChart3,
  Clock,
  CheckCircle,
  Phone,
} from 'lucide-react';
import { useState } from 'react';

interface Agent {
  id: string;
  name: string;
  description: string;
  language: string;
  voice: string;
  status: 'active' | 'inactive' | 'draft';
  totalCalls: number;
  successRate: number;
  avgDuration: string;
  lastUsed: string;
}

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const [showMenu, setShowMenu] = useState(false);

  const statusConfig = {
    active: {
      label: 'Active',
      color: 'text-success-500',
      bg: 'bg-success-500/10',
    },
    inactive: {
      label: 'Inactive',
      color: 'text-muted-foreground',
      bg: 'bg-muted',
    },
    draft: {
      label: 'Draft',
      color: 'text-warning-500',
      bg: 'bg-warning-500/10',
    },
  };

  return (
    <div
      className={cn(
        'relative p-6 rounded-2xl border border-border bg-card',
        'hover:shadow-lg transition-all duration-300 group'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex h-12 w-12 items-center justify-center rounded-xl',
              'bg-gradient-to-br from-primary-500/20 to-secondary-500/20'
            )}
          >
            <Bot className="h-6 w-6 text-primary-500" />
          </div>
          <div>
            <h3 className="font-semibold">{agent.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  statusConfig[agent.status].bg,
                  statusConfig[agent.status].color
                )}
              >
                {statusConfig[agent.status].label}
              </span>
              <span className="text-xs text-muted-foreground">
                {agent.language}
              </span>
            </div>
          </div>
        </div>

        {/* Menu */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg',
              'hover:bg-muted transition-colors',
              'opacity-0 group-hover:opacity-100'
            )}
          >
            <MoreVertical className="h-4 w-4 text-muted-foreground" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
              />
              <div
                className={cn(
                  'absolute right-0 top-full mt-1 w-48 z-20',
                  'rounded-xl border border-border bg-popover shadow-lg',
                  'animate-fade-in'
                )}
              >
                <div className="p-1">
                  <Link
                    href={`/dashboard/agents/${agent.id}`}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm"
                  >
                    <Edit className="h-4 w-4" />
                    Edit Agent
                  </Link>
                  <button className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm">
                    <Copy className="h-4 w-4" />
                    Duplicate
                  </button>
                  {agent.status === 'active' ? (
                    <button className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm text-warning-500">
                      <Pause className="h-4 w-4" />
                      Deactivate
                    </button>
                  ) : (
                    <button className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm text-success-500">
                      <Play className="h-4 w-4" />
                      Activate
                    </button>
                  )}
                  <div className="h-px bg-border my-1" />
                  <button className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-error-500/10 text-sm text-error-500">
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
        {agent.description}
      </p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="p-2 rounded-lg bg-muted/50 text-center">
          <Phone className="h-4 w-4 text-muted-foreground mx-auto mb-1" />
          <p className="text-sm font-medium">{agent.totalCalls.toLocaleString('en-US')}</p>
          <p className="text-xs text-muted-foreground">Calls</p>
        </div>
        <div className="p-2 rounded-lg bg-muted/50 text-center">
          <CheckCircle className="h-4 w-4 text-muted-foreground mx-auto mb-1" />
          <p className="text-sm font-medium">{agent.successRate}%</p>
          <p className="text-xs text-muted-foreground">Success</p>
        </div>
        <div className="p-2 rounded-lg bg-muted/50 text-center">
          <Clock className="h-4 w-4 text-muted-foreground mx-auto mb-1" />
          <p className="text-sm font-medium">{agent.avgDuration}</p>
          <p className="text-xs text-muted-foreground">Avg Time</p>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-border">
        <p className="text-xs text-muted-foreground">
          Voice: {agent.voice}
        </p>
        <p className="text-xs text-muted-foreground">{agent.lastUsed}</p>
      </div>

      {/* Hover actions */}
      <div
        className={cn(
          'absolute inset-0 flex items-center justify-center gap-3',
          'bg-background/80 backdrop-blur-sm rounded-2xl',
          'opacity-0 group-hover:opacity-100 transition-opacity'
        )}
      >
        <Link
          href={`/dashboard/agents/${agent.id}`}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg',
            'bg-primary-500 hover:bg-primary-600 text-white',
            'font-medium text-sm transition-colors'
          )}
        >
          <Edit className="h-4 w-4" />
          Edit
        </Link>
        <Link
          href={`/dashboard/agents/${agent.id}/test`}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg',
            'bg-secondary-500 hover:bg-secondary-600 text-white',
            'font-medium text-sm transition-colors'
          )}
        >
          <Play className="h-4 w-4" />
          Test
        </Link>
      </div>
    </div>
  );
}
