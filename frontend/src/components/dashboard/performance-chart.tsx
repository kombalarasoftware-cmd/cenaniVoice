'use client';

import { cn } from '@/lib/utils';
import { BarChart3 } from 'lucide-react';
import { useState } from 'react';

type TimeRange = '7d' | '30d' | '90d';

interface ChartData {
  date: string;
  calls: number;
  success: number;
}

const mockData: Record<TimeRange, ChartData[]> = {
  '7d': [
    { date: 'Mon', calls: 320, success: 248 },
    { date: 'Tue', calls: 450, success: 356 },
    { date: 'Wed', calls: 380, success: 298 },
    { date: 'Thu', calls: 520, success: 412 },
    { date: 'Fri', calls: 480, success: 378 },
    { date: 'Sat', calls: 220, success: 176 },
    { date: 'Sun', calls: 180, success: 145 },
  ],
  '30d': Array.from({ length: 30 }, (_, i) => ({
    date: `Day ${i + 1}`,
    calls: Math.floor(Math.random() * 500) + 200,
    success: Math.floor(Math.random() * 400) + 150,
  })),
  '90d': Array.from({ length: 12 }, (_, i) => ({
    date: `Week ${i + 1}`,
    calls: Math.floor(Math.random() * 3000) + 1500,
    success: Math.floor(Math.random() * 2500) + 1200,
  })),
};

export function PerformanceChart() {
  const [timeRange, setTimeRange] = useState<TimeRange>('7d');
  const data = mockData[timeRange];
  const maxValue = Math.max(...data.map((d) => d.calls));

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/10">
            <BarChart3 className="h-5 w-5 text-primary-500" />
          </div>
          <div>
            <h3 className="font-semibold">Performance Overview</h3>
            <p className="text-sm text-muted-foreground">Calls and success rate</p>
          </div>
        </div>

        {/* Time range selector */}
        <div className="flex items-center gap-1 p-1 rounded-lg bg-muted">
          {(['7d', '30d', '90d'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={cn(
                'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                timeRange === range
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 mb-6">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-primary-500" />
          <span className="text-sm text-muted-foreground">Total Calls</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-secondary-500" />
          <span className="text-sm text-muted-foreground">Successful</span>
        </div>
      </div>

      {/* Chart */}
      <div className="h-64 flex items-end gap-2">
        {data.slice(0, timeRange === '7d' ? 7 : timeRange === '30d' ? 15 : 12).map((item, index) => {
          const callsHeight = (item.calls / maxValue) * 100;
          const successHeight = (item.success / maxValue) * 100;

          return (
            <div
              key={index}
              className="flex-1 flex flex-col items-center gap-2 group"
            >
              {/* Bars container */}
              <div className="relative w-full h-52 flex items-end justify-center gap-1">
                {/* Calls bar */}
                <div
                  className={cn(
                    'w-[45%] rounded-t-md bg-primary-500/20 transition-all duration-300',
                    'group-hover:bg-primary-500/30'
                  )}
                  style={{ height: `${callsHeight}%` }}
                >
                  <div
                    className="w-full bg-primary-500 rounded-t-md transition-all duration-500"
                    style={{
                      height: '100%',
                      animationDelay: `${index * 50}ms`,
                    }}
                  />
                </div>
                {/* Success bar */}
                <div
                  className={cn(
                    'w-[45%] rounded-t-md bg-secondary-500/20 transition-all duration-300',
                    'group-hover:bg-secondary-500/30'
                  )}
                  style={{ height: `${successHeight}%` }}
                >
                  <div
                    className="w-full bg-secondary-500 rounded-t-md transition-all duration-500"
                    style={{
                      height: '100%',
                      animationDelay: `${index * 50 + 25}ms`,
                    }}
                  />
                </div>

                {/* Tooltip */}
                <div
                  className={cn(
                    'absolute -top-16 left-1/2 -translate-x-1/2 px-3 py-2 rounded-lg',
                    'bg-popover border border-border shadow-lg',
                    'opacity-0 group-hover:opacity-100 transition-opacity',
                    'pointer-events-none z-10 whitespace-nowrap'
                  )}
                >
                  <p className="text-xs font-medium">{item.date}</p>
                  <p className="text-xs text-muted-foreground">
                    Calls: <span className="text-primary-500">{item.calls}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Success: <span className="text-secondary-500">{item.success}</span>
                  </p>
                </div>
              </div>

              {/* Label */}
              <span className="text-xs text-muted-foreground truncate w-full text-center">
                {item.date}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
