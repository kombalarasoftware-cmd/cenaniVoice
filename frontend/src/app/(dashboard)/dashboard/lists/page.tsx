'use client';

import { Header } from '@/components/layout/header';
import { cn } from '@/lib/utils';
import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';
import {
  Plus,
  Search,
  ListChecks,
  Phone,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MoreVertical,
  Trash2,
  Eye,
  Edit2,
  Loader2,
  ArrowUpDown,
  RefreshCw,
} from 'lucide-react';

// ============ Types ============

interface DialList {
  id: number;
  name: string;
  description: string | null;
  status: string;
  total_numbers: number;
  active_numbers: number;
  completed_numbers: number;
  invalid_numbers: number;
  owner_id: number;
  agent_id: number | null;
  agent_name: string | null;
  created_at: string;
  updated_at: string;
}

interface AgentOption {
  id: number;
  name: string;
}

interface PaginatedResponse {
  items: DialList[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ============ Create List Modal ============

function CreateListModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}): React.ReactElement | null {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [agentId, setAgentId] = useState<number | null>(null);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingAgents, setIsLoadingAgents] = useState(false);

  useEffect(() => {
    if (!open) return;
    setIsLoadingAgents(true);
    api.get<AgentOption[]>('/agents')
      .then((data) => setAgents(data))
      .catch(() => setAgents([]))
      .finally(() => setIsLoadingAgents(false));
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error('List name is required');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post('/dial-lists/', {
        name: name.trim(),
        description: description.trim() || null,
        agent_id: agentId,
      });
      toast.success('List created successfully');
      setName('');
      setDescription('');
      setAgentId(null);
      onClose();
      onCreated();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create list');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-2xl shadow-2xl w-full max-w-md p-6 mx-4">
        <h2 className="text-xl font-semibold mb-4">Create New List</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5">List Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., January Campaign Leads"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500/50"
              autoFocus
              maxLength={255}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Agent</label>
            {isLoadingAgents ? (
              <div className="flex items-center gap-2 px-4 py-2.5 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading agents...
              </div>
            ) : (
              <select
                value={agentId ?? ''}
                onChange={(e) => setAgentId(e.target.value ? Number(e.target.value) : null)}
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500/50 appearance-none"
              >
                <option value="">— No Agent —</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            )}
            <p className="text-xs text-muted-foreground mt-1">Assign an agent to enable agent-level duplicate checking</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description for this list..."
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500/50 resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="px-4 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Create List
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ============ Status Badge ============

function StatusBadge({ status }: { status: string }): React.ReactElement {
  const config: Record<string, { label: string; className: string }> = {
    active: { label: 'Active', className: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' },
    inactive: { label: 'Inactive', className: 'bg-amber-500/10 text-amber-600 dark:text-amber-400' },
    archived: { label: 'Archived', className: 'bg-zinc-500/10 text-zinc-500' },
  };
  const c = config[status] || config.active;
  return (
    <span className={cn('inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium', c.className)}>
      {c.label}
    </span>
  );
}

// ============ Main Page ============

export default function ListsPage(): React.ReactElement {
  const router = useRouter();
  const [lists, setLists] = useState<DialList[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [actionMenuId, setActionMenuId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');

  const PAGE_SIZE = 20;

  const fetchLists = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: PAGE_SIZE.toString(),
      });
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);

      const data = await api.get<PaginatedResponse>(`/dial-lists/?${params.toString()}`);
      setLists(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err) {
      console.error('Failed to fetch lists:', err);
      toast.error('Failed to load lists');
    } finally {
      setIsLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchLists();
  }, [fetchLists]);

  // Debounced search
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const handleDelete = async (listId: number): Promise<void> => {
    if (!confirm('Are you sure you want to archive this list? Entries will be preserved.')) return;
    try {
      await api.delete(`/dial-lists/${listId}`);
      toast.success('List archived');
      fetchLists();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to archive list');
    }
    setActionMenuId(null);
  };

  const handleRename = async (listId: number): Promise<void> => {
    if (!editName.trim()) return;
    try {
      await api.put(`/dial-lists/${listId}`, { name: editName.trim() });
      toast.success('List renamed');
      setEditingId(null);
      fetchLists();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to rename list');
    }
  };

  const handleToggleStatus = async (list: DialList): Promise<void> => {
    const newStatus = list.status === 'active' ? 'inactive' : 'active';
    try {
      await api.put(`/dial-lists/${list.id}`, { status: newStatus });
      toast.success(`List ${newStatus === 'active' ? 'activated' : 'deactivated'}`);
      fetchLists();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update list status');
    }
    setActionMenuId(null);
  };

  // Summary stats
  const totalNumbers = lists.reduce((sum, l) => sum + l.total_numbers, 0);
  const activeNumbers = lists.reduce((sum, l) => sum + l.active_numbers, 0);
  const completedNumbers = lists.reduce((sum, l) => sum + l.completed_numbers, 0);

  return (
    <div className="min-h-screen">
      <Header
        title="Lists"
        description="Manage phone number lists for outbound campaigns"
      />

      <div className="p-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/10">
                <ListChecks className="h-5 w-5 text-primary-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{total}</p>
                <p className="text-xs text-muted-foreground">Total Lists</p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10">
                <Phone className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalNumbers.toLocaleString('en-US')}</p>
                <p className="text-xs text-muted-foreground">Total Numbers</p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10">
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{activeNumbers.toLocaleString('en-US')}</p>
                <p className="text-xs text-muted-foreground">Active (Dialable)</p>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10">
                <ArrowUpDown className="h-5 w-5 text-violet-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{completedNumbers.toLocaleString('en-US')}</p>
                <p className="text-xs text-muted-foreground">Completed</p>
              </div>
            </div>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search lists..."
                className="w-full pl-10 pr-4 py-2 rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary-500/50 text-sm"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchLists()}
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border hover:bg-muted transition-colors text-sm"
              title="Refresh"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-medium"
            >
              <Plus className="h-4 w-4" />
              New List
            </button>
          </div>
        </div>

        {/* List Table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
          </div>
        ) : lists.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-border rounded-2xl">
            <ListChecks className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No lists yet</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Create your first list to start uploading phone numbers
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors text-sm font-medium"
            >
              <Plus className="h-4 w-4" />
              Create List
            </button>
          </div>
        ) : (
          <>
            <div className="border border-border rounded-2xl overflow-hidden bg-card">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      List Name
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Agent
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Status
                    </th>
                    <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Total
                    </th>
                    <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Active
                    </th>
                    <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Completed
                    </th>
                    <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Invalid
                    </th>
                    <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Created
                    </th>
                    <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {lists.map((list) => (
                    <tr
                      key={list.id}
                      className="hover:bg-muted/20 transition-colors cursor-pointer"
                      onClick={() => router.push(`/dashboard/lists/${list.id}`)}
                    >
                      <td className="px-4 py-3">
                        {editingId === list.id ? (
                          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleRename(list.id);
                                if (e.key === 'Escape') setEditingId(null);
                              }}
                              className="px-2 py-1 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50"
                              autoFocus
                            />
                            <button
                              onClick={() => handleRename(list.id)}
                              className="text-xs text-primary-500 hover:underline"
                            >
                              Save
                            </button>
                          </div>
                        ) : (
                          <div>
                            <p className="font-medium text-sm">{list.name}</p>
                            {list.description && (
                              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                {list.description}
                              </p>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {list.agent_name ? (
                          <span className="text-sm">{list.agent_name}</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={list.status} />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm font-semibold">{list.total_numbers.toLocaleString('en-US')}</span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                          {list.active_numbers.toLocaleString('en-US')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                          {list.completed_numbers.toLocaleString('en-US')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm text-red-500 font-medium">
                          {list.invalid_numbers.toLocaleString('en-US')}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-muted-foreground">
                          {new Date(list.created_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="relative inline-block" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => setActionMenuId(actionMenuId === list.id ? null : list.id)}
                            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted transition-colors"
                          >
                            <MoreVertical className="h-4 w-4 text-muted-foreground" />
                          </button>
                          {actionMenuId === list.id && (
                            <div className="absolute right-0 top-full mt-1 w-44 bg-popover border border-border rounded-xl shadow-xl z-20 py-1">
                              <button
                                onClick={() => router.push(`/dashboard/lists/${list.id}`)}
                                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm hover:bg-muted transition-colors"
                              >
                                <Eye className="h-4 w-4" />
                                View Details
                              </button>
                              <button
                                onClick={() => {
                                  setEditingId(list.id);
                                  setEditName(list.name);
                                  setActionMenuId(null);
                                }}
                                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm hover:bg-muted transition-colors"
                              >
                                <Edit2 className="h-4 w-4" />
                                Rename
                              </button>
                              <button
                                onClick={() => handleToggleStatus(list)}
                                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm hover:bg-muted transition-colors"
                              >
                                {list.status === 'active' ? (
                                  <>
                                    <AlertTriangle className="h-4 w-4" />
                                    Deactivate
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle2 className="h-4 w-4" />
                                    Activate
                                  </>
                                )}
                              </button>
                              <div className="border-t border-border my-1" />
                              <button
                                onClick={() => handleDelete(list.id)}
                                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                              >
                                <Trash2 className="h-4 w-4" />
                                Archive
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-between mt-4 px-2">
                <p className="text-sm text-muted-foreground">
                  Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  {Array.from({ length: Math.min(5, pages) }, (_, i) => {
                    let p: number;
                    if (pages <= 5) {
                      p = i + 1;
                    } else if (page <= 3) {
                      p = i + 1;
                    } else if (page >= pages - 2) {
                      p = pages - 4 + i;
                    } else {
                      p = page - 2 + i;
                    }
                    return (
                      <button
                        key={p}
                        onClick={() => setPage(p)}
                        className={cn(
                          'flex h-8 w-8 items-center justify-center rounded-lg text-sm transition-colors',
                          p === page
                            ? 'bg-primary-500 text-white'
                            : 'border border-border hover:bg-muted'
                        )}
                      >
                        {p}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => setPage(Math.min(pages, page + 1))}
                    disabled={page === pages}
                    className="px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Close action menu on outside click */}
      {actionMenuId !== null && (
        <div className="fixed inset-0 z-10" onClick={() => setActionMenuId(null)} />
      )}

      {/* Create Modal */}
      <CreateListModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreated={fetchLists}
      />
    </div>
  );
}
