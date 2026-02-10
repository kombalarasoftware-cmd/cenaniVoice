'use client';

import { Header } from '@/components/layout/header';
import { AgentCard } from '@/components/agents/agent-card';
import { CreateAgentDialog } from '@/components/agents/create-agent-dialog';
import { useState, useEffect } from 'react';
import { Bot, Plus, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { API_V1 } from '@/lib/api';

// Helper function to format last used time
function formatLastUsed(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US');
}

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

export default function AgentsPage() {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive' | 'draft'>('all');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAgents = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_V1}/agents`, {
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        // Map API response to frontend format
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const mappedAgents: Agent[] = data.map((agent: any) => ({
          id: String(agent.id),
          name: agent.name || '',
          description: agent.description || '',
          language: agent.language === 'en' ? 'English' : agent.language === 'tr' ? 'Turkish' : agent.language === 'de' ? 'German' : agent.language === 'fr' ? 'French' : agent.language === 'es' ? 'Spanish' : String(agent.language || ''),
          voice: agent.voice ? String(agent.voice).charAt(0).toUpperCase() + String(agent.voice).slice(1) : 'Alloy',
          status: (agent.status || 'draft').toLowerCase() as 'active' | 'inactive' | 'draft',
          totalCalls: Number(agent.total_calls) || 0,
          successRate: Number(agent.total_calls) > 0 ? (Number(agent.successful_calls) / Number(agent.total_calls) * 100) : 0,
          avgDuration: agent.avg_duration ? `${Math.floor(Number(agent.avg_duration) / 60)}:${(Number(agent.avg_duration) % 60).toString().padStart(2, '0')}` : '-',
          lastUsed: agent.updated_at ? formatLastUsed(String(agent.updated_at)) : 'Never used',
          isSystem: agent.is_system || false,
        }));
        setAgents(mappedAgents);
      }
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  // Refresh after dialog closes
  const handleDialogClose = (open: boolean) => {
    setShowCreateDialog(open);
    if (!open) {
      fetchAgents();
    }
  };

  const filteredAgents = agents.filter((agent) => {
    if (filter === 'all') return true;
    return agent.status === filter;
  });

  return (
    <div className="min-h-screen">
      <Header
        title="AI Agents"
        description="Manage your voice agents"
        action={{
          label: 'Create Agent',
          onClick: () => setShowCreateDialog(true),
        }}
      />

      <div className="p-6">
        {/* Filter tabs */}
        <div className="flex items-center gap-2 mb-6">
          {(['all', 'active', 'inactive', 'draft'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                filter === status
                  ? 'bg-primary-500 text-white'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              )}
            >
              {status === 'all' && 'All Agents'}
              {status === 'active' && 'Active'}
              {status === 'inactive' && 'Inactive'}
              {status === 'draft' && 'Draft'}
            </button>
          ))}
        </div>

        {/* Agents grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Create new card */}
            <button
              onClick={() => setShowCreateDialog(true)}
              className={cn(
                'flex flex-col items-center justify-center gap-4 p-8',
                'rounded-2xl border-2 border-dashed border-border',
                'hover:border-primary-500 hover:bg-primary-500/5',
                'transition-all duration-300 group min-h-[280px]'
              )}
            >
              <div
                className={cn(
                  'flex h-16 w-16 items-center justify-center rounded-2xl',
                  'bg-muted group-hover:bg-primary-500/10 transition-colors'
                )}
              >
                <Plus className="h-8 w-8 text-muted-foreground group-hover:text-primary-500 transition-colors" />
              </div>
              <div className="text-center">
                <p className="font-semibold group-hover:text-primary-500 transition-colors">
                  Create New Agent
                </p>
                <p className="text-sm text-muted-foreground">
                  Start from scratch or use a template
                </p>
              </div>
            </button>

            {/* Agent cards */}
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} onRefresh={fetchAgents} />
            ))}
          </div>
        )}
      </div>

      {/* Create dialog */}
      <CreateAgentDialog
        open={showCreateDialog}
        onOpenChange={handleDialogClose}
      />
    </div>
  );
}
