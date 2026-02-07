'use client';

import { Header } from '@/components/layout/header';
import { StatsCard } from '@/components/dashboard/stats-card';
import { LiveCallsWidget } from '@/components/dashboard/live-calls-widget';
import { CampaignProgress } from '@/components/dashboard/campaign-progress';
import { RecentActivity } from '@/components/dashboard/recent-activity';
import { PerformanceChart } from '@/components/dashboard/performance-chart';
import { CustomerProfileCard } from '@/components/dashboard/customer-profile-card';
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
            value={23}
            change={5}
            changeLabel="vs last hour"
            trend="up"
            icon={PhoneCall}
            color="primary"
            live
          />
          <StatsCard
            title="Today's Calls"
            value={1847}
            change={12.5}
            changeLabel="vs yesterday"
            trend="up"
            icon={TrendingUp}
            color="secondary"
          />
          <StatsCard
            title="Success Rate"
            value="78.4%"
            change={3.2}
            changeLabel="vs last week"
            trend="up"
            icon={CheckCircle}
            color="success"
          />
          <StatsCard
            title="Avg Duration"
            value="2:34"
            change={-15}
            changeLabel="seconds"
            trend="down"
            icon={Clock}
            color="accent"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Live Calls - Takes 2 columns */}
          <div className="lg:col-span-2">
            <LiveCallsWidget />
          </div>

          {/* Customer Profile & Recent Activity */}
          <div className="space-y-6">
            <CustomerProfileCard />
            <RecentActivity />
          </div>
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Performance Chart */}
          <PerformanceChart />

          {/* Campaign Progress */}
          <CampaignProgress />
        </div>
      </div>
    </div>
  );
}
