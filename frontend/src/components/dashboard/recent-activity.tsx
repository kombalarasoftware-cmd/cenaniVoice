'use client';

import { cn } from '@/lib/utils';
import {
  Activity,
  PhoneIncoming,
  PhoneOutgoing,
  PhoneMissed,
  CheckCircle,
  XCircle,
  UserPlus,
} from 'lucide-react';

interface ActivityItem {
  id: string;
  type: 'call_completed' | 'call_failed' | 'campaign_started' | 'campaign_completed' | 'number_uploaded';
  title: string;
  description: string;
  timestamp: string;
}

const mockActivities: ActivityItem[] = [
  {
    id: '1',
    type: 'call_completed',
    title: 'Call Completed',
    description: '+90 532 XXX XX 12 - Ödeme sözü alındı',
    timestamp: '2 min ago',
  },
  {
    id: '2',
    type: 'call_failed',
    title: 'Call Failed',
    description: '+90 535 XXX XX 45 - No answer',
    timestamp: '5 min ago',
  },
  {
    id: '3',
    type: 'campaign_started',
    title: 'Campaign Started',
    description: 'Randevu Hatırlatma campaign activated',
    timestamp: '15 min ago',
  },
  {
    id: '4',
    type: 'call_completed',
    title: 'Call Completed',
    description: '+90 542 XXX XX 78 - Transferred to human',
    timestamp: '18 min ago',
  },
  {
    id: '5',
    type: 'number_uploaded',
    title: 'Numbers Uploaded',
    description: '500 numbers added to Anket campaign',
    timestamp: '1 hour ago',
  },
  {
    id: '6',
    type: 'campaign_completed',
    title: 'Campaign Completed',
    description: 'Müşteri Memnuniyet Anketi finished',
    timestamp: '2 hours ago',
  },
];

export function RecentActivity() {
  const getIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'call_completed':
        return { icon: CheckCircle, color: 'text-success-500', bg: 'bg-success-500/10' };
      case 'call_failed':
        return { icon: XCircle, color: 'text-error-500', bg: 'bg-error-500/10' };
      case 'campaign_started':
        return { icon: PhoneOutgoing, color: 'text-primary-500', bg: 'bg-primary-500/10' };
      case 'campaign_completed':
        return { icon: CheckCircle, color: 'text-secondary-500', bg: 'bg-secondary-500/10' };
      case 'number_uploaded':
        return { icon: UserPlus, color: 'text-accent-500', bg: 'bg-accent-500/10' };
      default:
        return { icon: Activity, color: 'text-muted-foreground', bg: 'bg-muted' };
    }
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-6 h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-500/10">
            <Activity className="h-5 w-5 text-accent-500" />
          </div>
          <div>
            <h3 className="font-semibold">Recent Activity</h3>
            <p className="text-sm text-muted-foreground">Latest updates</p>
          </div>
        </div>
      </div>

      {/* Activity list */}
      <div className="space-y-4">
        {mockActivities.map((activity, index) => {
          const { icon: Icon, color, bg } = getIcon(activity.type);
          return (
            <div
              key={activity.id}
              className={cn(
                'flex items-start gap-3 animate-fade-in',
                index > 0 && 'pt-4 border-t border-border'
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className={cn('flex h-8 w-8 items-center justify-center rounded-lg flex-shrink-0', bg)}>
                <Icon className={cn('h-4 w-4', color)} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{activity.title}</p>
                <p className="text-sm text-muted-foreground truncate">
                  {activity.description}
                </p>
              </div>
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {activity.timestamp}
              </span>
            </div>
          );
        })}
      </div>

      {/* View all link */}
      <div className="mt-6 text-center">
        <a
          href="/dashboard/calls"
          className="text-sm text-primary-500 hover:text-primary-600 font-medium"
        >
          View all activity →
        </a>
      </div>
    </div>
  );
}
