'use client';

import { Header } from '@/components/layout/header';
import { StatsCard } from '@/components/dashboard/stats-card';
import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { formatDuration } from '@/lib/utils';
import {
  PhoneCall,
  CheckCircle,
  Clock,
  TrendingUp,
} from 'lucide-react';

interface DashboardStats {
  active_calls: number;
  active_calls_change: number;
  today_calls: number;
  today_calls_change: number;
  success_rate: number;
  success_rate_change: number;
  avg_duration: number;
  avg_duration_change: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats>({
    active_calls: 0,
    active_calls_change: 0,
    today_calls: 0,
    today_calls_change: 0,
    success_rate: 0,
    success_rate_change: 0,
    avg_duration: 0,
    avg_duration_change: 0,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.get<DashboardStats>('/reports/dashboard');
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="min-h-screen">
      <Header
        title="Dashboard"
        description="Overview of your voice AI platform"
        action={{
          label: 'New Campaign',
          onClick: () => router.push('/dashboard/campaigns/create'),
        }}
      />

      <div className="p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Active Calls"
            value={stats.active_calls}
            change={stats.active_calls_change}
            changeLabel="vs last hour"
            trend="up"
            icon={PhoneCall}
            color="primary"
            live
          />
          <StatsCard
            title="Today's Calls"
            value={stats.today_calls}
            change={stats.today_calls_change}
            changeLabel="vs yesterday"
            trend="up"
            icon={TrendingUp}
            color="secondary"
          />
          <StatsCard
            title="Success Rate"
            value={`${stats.success_rate}%`}
            change={stats.success_rate_change}
            changeLabel="vs last week"
            trend="up"
            icon={CheckCircle}
            color="success"
          />
          <StatsCard
            title="Avg Duration"
            value={formatDuration(stats.avg_duration)}
            change={stats.avg_duration_change}
            changeLabel="seconds"
            trend="down"
            icon={Clock}
            color="accent"
          />
        </div>
      </div>
    </div>
  );
}
