'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { API_V1 } from '@/lib/api';
import {
  Calendar,
  Clock,
  User,
  Phone,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Appointment {
  id: number;
  call_id?: number;
  agent_id?: number;
  campaign_id?: number;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  customer_address?: string;
  appointment_type: string;
  appointment_date: string;
  appointment_time?: string;
  duration_minutes: number;
  status: string;
  notes?: string;
  location?: string;
  created_at: string;
  updated_at: string;
  confirmed_at?: string;
  agent_name?: string;
  campaign_name?: string;
}

interface Stats {
  total: number;
  today: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
}

const statusConfig: Record<string, { label: string; color: string; icon: any }> = {
  pending: { label: 'Pending', color: 'bg-yellow-500', icon: AlertCircle },
  confirmed: { label: 'Confirmed', color: 'bg-green-500', icon: CheckCircle },
  cancelled: { label: 'Cancelled', color: 'bg-red-500', icon: XCircle },
  completed: { label: 'Completed', color: 'bg-blue-500', icon: CheckCircle },
  no_show: { label: 'No Show', color: 'bg-gray-500', icon: XCircle },
};

const typeConfig: Record<string, string> = {
  consultation: 'Consultation',
  site_visit: 'Site Visit',
  installation: 'Installation',
  maintenance: 'Maintenance',
  demo: 'Demo',
  other: 'Other',
};

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchAppointments();
    fetchStats();
  }, [page, statusFilter, typeFilter]);

  const fetchAppointments = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
      });
      
      if (statusFilter) params.append('status', statusFilter);
      if (typeFilter) params.append('appointment_type', typeFilter);
      if (searchQuery) params.append('search', searchQuery);
      
      const response = await fetch(`${API_V1}/appointments/?${params}`);
      if (!response.ok) throw new Error('Failed to fetch appointments');
      
      const data = await response.json();
      setAppointments(data.items);
      setTotalPages(data.pages);
      setTotal(data.total);
    } catch (error) {
      console.error('Fetch error:', error);
      toast.error('Failed to load appointments');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_V1}/appointments/stats`);
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
    fetchAppointments();
  };

  const handleStatusChange = async (appointmentId: number, action: 'cancel' | 'complete') => {
    try {
      const endpoint = action === 'cancel' ? 'cancel' : 'complete';
      const response = await fetch(`${API_V1}/appointments/${appointmentId}/${endpoint}`, {
        method: 'POST',
      });
      
      if (!response.ok) throw new Error('Action failed');
      
      toast.success(action === 'cancel' ? 'Appointment cancelled' : 'Appointment marked as completed');
      fetchAppointments();
      fetchStats();
    } catch (error) {
      toast.error('Operation failed');
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Appointments</h1>
          <p className="text-muted-foreground">Appointments created from AI conversations</p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Today</p>
            <p className="text-2xl font-bold text-primary-500">{stats.today}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Confirmed</p>
            <p className="text-2xl font-bold text-green-500">{stats.by_status?.confirmed || 0}</p>
          </div>
          <div className="p-4 bg-card rounded-xl border border-border">
            <p className="text-sm text-muted-foreground">Completed</p>
            <p className="text-2xl font-bold text-blue-500">{stats.by_status?.completed || 0}</p>
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
              placeholder="Search customer name or phone..."
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
          <option value="confirmed">Confirmed</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
          <option value="no_show">No Show</option>
        </select>
        
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 bg-muted/30 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Types</option>
          <option value="consultation">Consultation</option>
          <option value="site_visit">Site Visit</option>
          <option value="installation">Installation</option>
          <option value="maintenance">Maintenance</option>
          <option value="demo">Demo</option>
        </select>
      </div>

      {/* Appointments List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        </div>
      ) : appointments.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No appointments yet</p>
          <p className="text-sm">Appointments from AI conversations will appear here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {appointments.map((apt) => {
            const statusInfo = statusConfig[apt.status] || statusConfig.pending;
            const StatusIcon = statusInfo.icon;
            
            return (
              <div
                key={apt.id}
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
                      <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {typeConfig[apt.appointment_type] || apt.appointment_type}
                      </span>
                      {apt.agent_name && (
                        <span className="text-xs text-muted-foreground">
                          Agent: {apt.agent_name}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{apt.customer_name || 'Unnamed'}</span>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {formatDate(apt.appointment_date)}
                      </div>
                      {apt.appointment_time && (
                        <div className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {apt.appointment_time}
                        </div>
                      )}
                      {apt.customer_phone && (
                        <div className="flex items-center gap-1">
                          <Phone className="h-4 w-4" />
                          {apt.customer_phone}
                        </div>
                      )}
                      {apt.customer_address && (
                        <div className="flex items-center gap-1">
                          <MapPin className="h-4 w-4" />
                          <span className="truncate max-w-[200px]">{apt.customer_address}</span>
                        </div>
                      )}
                    </div>
                    
                    {apt.notes && (
                      <p className="text-sm text-muted-foreground italic">
                        {apt.notes}
                      </p>
                    )}
                  </div>
                  
                  {/* Actions */}
                  {apt.status === 'confirmed' && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleStatusChange(apt.id, 'complete')}
                        className="px-3 py-1.5 text-xs bg-green-500/10 text-green-500 rounded-lg hover:bg-green-500/20 transition-colors"
                      >
                        Completed
                      </button>
                      <button
                        onClick={() => handleStatusChange(apt.id, 'cancel')}
                        className="px-3 py-1.5 text-xs bg-red-500/10 text-red-500 rounded-lg hover:bg-red-500/20 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
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
            Total {total} appointments
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg border border-border hover:bg-muted/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg border border-border hover:bg-muted/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
