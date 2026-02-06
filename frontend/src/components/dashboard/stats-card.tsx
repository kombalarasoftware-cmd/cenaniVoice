'use client';

import { cn } from '@/lib/utils';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';
import { useEffect, useState } from 'react';

interface StatsCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  trend?: 'up' | 'down';
  icon: LucideIcon;
  color?: 'primary' | 'secondary' | 'success' | 'accent' | 'error';
  live?: boolean;
}

export function StatsCard({
  title,
  value,
  change,
  changeLabel,
  trend,
  icon: Icon,
  color = 'primary',
  live,
}: StatsCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0;

  // Animate number counting
  useEffect(() => {
    if (typeof value !== 'number') {
      setDisplayValue(numericValue);
      return;
    }

    const duration = 1000;
    const steps = 30;
    const increment = numericValue / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= numericValue) {
        setDisplayValue(numericValue);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [numericValue, value]);

  const colorClasses = {
    primary: {
      bg: 'bg-primary-500/10',
      text: 'text-primary-500',
      glow: 'shadow-primary-500/20',
    },
    secondary: {
      bg: 'bg-secondary-500/10',
      text: 'text-secondary-500',
      glow: 'shadow-secondary-500/20',
    },
    success: {
      bg: 'bg-success-500/10',
      text: 'text-success-500',
      glow: 'shadow-success-500/20',
    },
    accent: {
      bg: 'bg-accent-500/10',
      text: 'text-accent-500',
      glow: 'shadow-accent-500/20',
    },
    error: {
      bg: 'bg-error-500/10',
      text: 'text-error-500',
      glow: 'shadow-error-500/20',
    },
  };

  return (
    <div
      className={cn(
        'relative p-6 rounded-2xl border border-border',
        'bg-card hover:shadow-lg transition-all duration-300',
        'group overflow-hidden'
      )}
    >
      {/* Background gradient on hover */}
      <div
        className={cn(
          'absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300',
          'bg-gradient-to-br from-transparent via-transparent',
          color === 'primary' && 'to-primary-500/5',
          color === 'secondary' && 'to-secondary-500/5',
          color === 'success' && 'to-success-500/5',
          color === 'accent' && 'to-accent-500/5',
          color === 'error' && 'to-error-500/5'
        )}
      />

      <div className="relative flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {typeof value === 'number' ? displayValue : value}
            </span>
            {live && (
              <span className="flex items-center gap-1">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-error-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-error-500" />
                </span>
                <span className="text-xs text-error-500 font-medium">LIVE</span>
              </span>
            )}
          </div>

          {change !== undefined && (
            <div className="flex items-center gap-1.5">
              {trend === 'up' ? (
                <TrendingUp className="h-4 w-4 text-success-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-error-500" />
              )}
              <span
                className={cn(
                  'text-sm font-medium',
                  trend === 'up' ? 'text-success-500' : 'text-error-500'
                )}
              >
                {change > 0 ? '+' : ''}
                {change}%
              </span>
              {changeLabel && (
                <span className="text-sm text-muted-foreground">{changeLabel}</span>
              )}
            </div>
          )}
        </div>

        {/* Icon */}
        <div
          className={cn(
            'flex h-12 w-12 items-center justify-center rounded-xl',
            colorClasses[color].bg
          )}
        >
          <Icon className={cn('h-6 w-6', colorClasses[color].text)} />
        </div>
      </div>
    </div>
  );
}
