'use client';

import { cn } from '@/lib/utils';
import { API_V1 } from '@/lib/api';
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
  Shield,
  Loader2,
  AlertTriangle,
  X,
} from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

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
  isSystem?: boolean;
}

interface AgentCardProps {
  agent: Agent;
  onRefresh?: () => void;
}

export function AgentCard({ agent, onRefresh }: AgentCardProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmName, setDeleteConfirmName] = useState('');

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

  const handleDuplicate = async () => {
    setIsLoading(true);
    setShowMenu(false);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_V1}/agents/${agent.id}/duplicate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });
      
      if (response.ok) {
        toast.success('Agent duplicated');
        onRefresh?.();
      } else {
        throw new Error('Duplication failed');
      }
    } catch (error) {
      toast.error('Failed to duplicate agent');
    } finally {
      setIsLoading(false);
    }
  };

  const openDeleteDialog = () => {
    setShowMenu(false);
    setDeleteConfirmName('');
    setShowDeleteDialog(true);
  };

  const handleDelete = async () => {
    if (deleteConfirmName !== agent.name) {
      toast.error('Agent name doesn\'t match');
      return;
    }
    
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_V1}/agents/${agent.id}`, {
        method: 'DELETE',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });
      
      if (response.ok) {
        toast.success('Agent deleted');
        setShowDeleteDialog(false);
        onRefresh?.();
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Delete failed');
      }
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete agent');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStatusChange = async (action: 'activate' | 'deactivate') => {
    setIsLoading(true);
    setShowMenu(false);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_V1}/agents/${agent.id}/${action}`, {
        method: 'POST',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });
      
      if (response.ok) {
        toast.success(action === 'activate' ? 'Agent activated' : 'Agent deactivated');
        onRefresh?.();
      } else {
        throw new Error('Operation failed');
      }
    } catch (error) {
      toast.error('Failed to change status');
    } finally {
      setIsLoading(false);
    }
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
        <div className="relative z-20">
          <button
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg',
              'hover:bg-muted transition-colors bg-card/80'
            )}
          >
            <MoreVertical className="h-4 w-4 text-muted-foreground" />
          </button>

          {showMenu && (
            <>
              <div
                className="fixed inset-0 z-30"
                onClick={() => setShowMenu(false)}
              />
              <div
                className={cn(
                  'absolute right-0 top-full mt-1 w-48 z-40',
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
                    Edit
                  </Link>
                  <button 
                    onClick={handleDuplicate}
                    disabled={isLoading}
                    className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm disabled:opacity-50"
                  >
                    <Copy className="h-4 w-4" />
                    Duplicate
                  </button>
                  {agent.status === 'active' ? (
                    <button 
                      onClick={() => handleStatusChange('deactivate')}
                      disabled={isLoading}
                      className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm text-warning-500 disabled:opacity-50"
                    >
                      <Pause className="h-4 w-4" />
                      Deactivate
                    </button>
                  ) : (
                    <button 
                      onClick={() => handleStatusChange('activate')}
                      disabled={isLoading}
                      className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-muted text-sm text-success-500 disabled:opacity-50"
                    >
                      <Play className="h-4 w-4" />
                      Activate
                    </button>
                  )}
                  <div className="h-px bg-border my-1" />
                  {agent.isSystem ? (
                    <div className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground">
                      <Shield className="h-4 w-4" />
                      System Agent
                    </div>
                  ) : (
                    <button 
                      onClick={openDeleteDialog}
                      disabled={isLoading}
                      className="flex w-full items-center gap-2 px-3 py-2 rounded-lg hover:bg-error-500/10 text-sm text-error-500 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </button>
                  )}
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
          'opacity-0 group-hover:opacity-100 transition-opacity',
          'pointer-events-none z-10'
        )}
      >
        <Link
          href={`/dashboard/agents/${agent.id}`}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg',
            'bg-primary-500 hover:bg-primary-600 text-white',
            'font-medium text-sm transition-colors',
            'pointer-events-auto'
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
            'font-medium text-sm transition-colors',
            'pointer-events-auto'
          )}
        >
          <Play className="h-4 w-4" />
          Test
        </Link>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md mx-4 animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-error-500/10">
                  <AlertTriangle className="h-5 w-5 text-error-500" />
                </div>
                <h3 className="font-semibold text-lg">Delete Agent</h3>
              </div>
              <button
                onClick={() => setShowDeleteDialog(false)}
                className="p-1 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              <div className="p-3 bg-error-500/10 border border-error-500/20 rounded-lg">
                <p className="text-sm text-error-500">
                  <strong>Warning:</strong> This action cannot be undone. The agent and all associated data will be permanently deleted.
                </p>
              </div>

              <p className="text-sm text-muted-foreground">
                To delete <strong className="text-foreground">&quot;{agent.name}&quot;</strong>, type the agent name below:
              </p>

              <input
                type="text"
                value={deleteConfirmName}
                onChange={(e) => setDeleteConfirmName(e.target.value)}
                placeholder={agent.name}
                className={cn(
                  'w-full px-4 py-3 rounded-lg border bg-muted/30',
                  'focus:outline-none focus:ring-2 focus:ring-error-500',
                  deleteConfirmName === agent.name ? 'border-error-500' : 'border-border'
                )}
              />
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
              <button
                onClick={() => setShowDeleteDialog(false)}
                className="px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteConfirmName !== agent.name || isLoading}
                className={cn(
                  'px-4 py-2 rounded-lg font-medium transition-colors',
                  'bg-error-500 text-white hover:bg-error-600',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Permanently Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
