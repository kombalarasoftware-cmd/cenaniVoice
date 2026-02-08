'use client';

import { Header } from '@/components/layout/header';
import { StatsCard } from '@/components/dashboard/stats-card';
import {
  PhoneCall,
  CheckCircle,
  Clock,
  TrendingUp,
} from 'lucide-react';

export default function DashboardPage() {
  return (
    <div className="min-h-screen">
      <Header
        title="Dashboard"
        description="Overview of your voice AI platform"
        action={{
          label: 'New Campaign',
          onClick: () => console.log('New campaign'),
        }}
      />

      <div className="p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Active Calls"
            value={0}
            change={0}
            changeLabel="vs last hour"
            trend="up"
            icon={PhoneCall}
            color="primary"
            live
          />
          <StatsCard
            title="Today's Calls"
            value={0}
            change={0}
            changeLabel="vs yesterday"
            trend="up"
            icon={TrendingUp}
            color="secondary"
          />
          <StatsCard
            title="Success Rate"
            value="0%"
            change={0}
            changeLabel="vs last week"
            trend="up"
            icon={CheckCircle}
            color="success"
          />
          <StatsCard
            title="Avg Duration"
            value="0:00"
            change={0}
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
