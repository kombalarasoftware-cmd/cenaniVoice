'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { API_V1 } from '@/lib/api';
import {
  Users,
  Phone,
  Mail,
  MapPin,
  Star,
  Tag,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  Clock,
  XCircle,
  UserPlus,
  MessageSquare,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Lead {
  id: number;
  call_id?: number;
  agent_id?: number;
  campaign_id?: number;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  customer_address?: string;
  interest_type: string;
  customer_statement?: string;
  status: string;
  priority: number;
  notes?: string;
  follow_up_date?: string;
  follow_up_notes?: string;
  contacted_at?: string;
  converted_at?: string;
  created_at: string;
  updated_at: string;
  agent_name?: string;
  campaign_name?: string;
}

interface Stats {
  total: number;
  today: number;
  by_status: Record<string, number>;
  by_interest_type: Record<string, number>;
  by_priority: Record<string, number>;
}

const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  new: { label: 'New', color: 'bg-blue-500', icon: UserPlus },
  contacted: { label: 'Contacted', color: 'bg-yellow-500', icon: Phone },
  qualified: { label: 'Qualified', color: 'bg-purple-500', icon: Star },
  converted: { label: 'Converted', color: 'bg-green-500', icon: CheckCircle },
  lost: { label: 'Lost', color: 'bg-red-500', icon: XCircle },
};

const interestTypeConfig: Record<string, string> = {
  callback: 'Callback Request',
  address_collection: 'Address Info',
  purchase_intent: 'Purchase Intent',
  demo_request: 'Demo Request',
  quote_request: 'Quote Request',
  subscription: 'Subscription/Membership',
  information: 'Information Request',
  other: 'Other',
};

const priorityConfig: Record<number, { label: string; color: string }> = {
  1: { label: 'High', color: 'bg-red-500' },
  2: { label: 'Medium', color: 'bg-yellow-500' },
  3: { label: 'Low', color: 'bg-gray-500' },
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [interestFilter, setInterestFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  // Edit modal state
  const [editingLead, setEditingLead] = useState<Lead | null>(null);

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [page, statusFilter, interestFilter, priorityFilter]);

  const fetchLeads = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
      });
      
      if (statusFilter) params.append('status', statusFilter);
      if (interestFilter) params.append('interest_type', interestFilter);
      if (priorityFilter) params.append('priority', priorityFilter);
      if (searchQuery) params.append('search', searchQuery);
      
      const response = await fetch(`${API_V1}/leads/?${params}`);
      if (!response.ok) throw new Error('Failed to fetch leads');
      
      const data = await response.json();
      setLeads(data.items);
      setTotalPages(data.pages);
      setTotal(data.total);
    } catch (error) {
      console.error('Fetch error:', error);
      toast.error('Failed to load leads');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_V1}/leads/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Stats fetch error:', error);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLeads();
  };

  const handleStatusChange = async (leadId: number, newStatus: string) => {
    try {
      const response = await fetch(`${API_V1}/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      
      if (!response.ok) throw new Error('Update failed');
      
      toast.success('Lead status updated');
      fetchLeads();
      fetchStats();
    } catch (error) {
      toast.error('Update failed');
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Leads</h1>
          <p className="text-muted-foreground">Leads captured from AI conversations</p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Today</p>
            <p className="text-2xl font-bold text-primary-500">{stats.today}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">New</p>
            <p className="text-2xl font-bold text-blue-500">{stats.by_status?.new || 0}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Qualified</p>
            <p className="text-2xl font-bold text-purple-500">{stats.by_status?.qualified || 0}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Converted</p>
            <p className="text-2xl font-bold text-green-500">{stats.by_status?.converted || 0}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search name, phone or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-muted/30 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </form>
        
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 bg-muted/30 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="qualified">Qualified</option>
          <option value="converted">Converted</option>
          <option value="lost">Lost</option>
        </select>
        
        <select
          value={interestFilter}
          onChange={(e) => { setInterestFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 bg-muted/30 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Interest Types</option>
          <option value="callback">Callback</option>
          <option value="subscription">Subscription</option>
          <option value="purchase_intent">Purchase</option>
          <option value="demo_request">Demo</option>
          <option value="quote_request">Quote</option>
          <option value="information">Information</option>
        </select>
        
        <select
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 bg-muted/30 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Priorities</option>
          <option value="1">High</option>
          <option value="2">Medium</option>
          <option value="3">Low</option>
        </select>
      </div>

      {/* Leads List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        </div>
      ) : leads.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No leads yet</p>
          <p className="text-sm">Leads captured from AI conversations will appear here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {leads.map((lead) => {
            const statusInfo = statusConfig[lead.status] || statusConfig.new;
            const StatusIcon = statusInfo.icon;
            const priorityInfo = priorityConfig[lead.priority] || priorityConfig[2];
            
            return (
              <div
                key={lead.id}
                className="p-4 bg-card rounded-xl border border-border hover:border-primary-500/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      <span className={cn(
                        "px-2 py-0.5 text-xs font-medium text-white rounded",
                        statusInfo.color
                      )}>
                        {statusInfo.label}
                      </span>
                      <span className={cn(
                        "px-2 py-0.5 text-xs font-medium text-white rounded",
                        priorityInfo.color
                      )}>
                        {priorityInfo.label} Priority
                      </span>
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {interestTypeConfig[lead.interest_type] || lead.interest_type}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{lead.customer_name || 'Unnamed'}</span>
                      {lead.agent_name && (
                        <span className="text-xs text-muted-foreground">
                          via {lead.agent_name}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                      {lead.customer_phone && (
                        <div className="flex items-center gap-1">
                          <Phone className="h-4 w-4" />
                          {lead.customer_phone}
                        </div>
                      )}
                      {lead.customer_email && (
                        <div className="flex items-center gap-1">
                          <Mail className="h-4 w-4" />
                          {lead.customer_email}
                        </div>
                      )}
                      {lead.customer_address && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-4 w-4" />
                          <span className="truncate max-w-[200px]">{lead.customer_address}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4" />
                        {formatDate(lead.created_at)}
                      </div>
                    </div>

                    {lead.customer_statement && (
                      <div className="flex items-start gap-2 mt-2 p-2 bg-muted/30 rounded-lg">
                        <MessageSquare className="h-4 w-4 text-muted-foreground mt-0.5" />
                        <p className="text-sm italic text-muted-foreground">
                          &quot;{lead.customer_statement}&quot;
                        </p>
                      </div>
                    )}
                  </div>
                  
                  {/* Quick Actions */}
                  <div className="flex flex-col gap-2">
                    {lead.status === 'new' && (
                      <button
                        onClick={() => handleStatusChange(lead.id, 'contacted')}
                        className="px-3 py-1.5 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
                      >
                        Contacted
                      </button>
                    )}
                    {lead.status === 'contacted' && (
                      <button
                        onClick={() => handleStatusChange(lead.id, 'qualified')}
                        className="px-3 py-1.5 text-xs bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
                      >
                        Mark as Qualified
                      </button>
                    )}
                    {(lead.status === 'qualified' || lead.status === 'contacted') && (
                      <button
                        onClick={() => handleStatusChange(lead.id, 'converted')}
                        className="px-3 py-1.5 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                      >
                        Converted
                      </button>
                    )}
                    {lead.status !== 'lost' && lead.status !== 'converted' && (
                      <button
                        onClick={() => handleStatusChange(lead.id, 'lost')}
                        className="px-3 py-1.5 text-xs bg-muted text-muted-foreground rounded hover:bg-red-500 hover:text-white transition-colors"
                      >
                        Lost
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Total {total} leads, Page {page} / {totalPages}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
