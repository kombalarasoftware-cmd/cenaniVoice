'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

type VisualizerMode = 'waveform' | 'bars' | 'circular' | 'particles';

interface VoiceVisualizerProps {
  mode?: VisualizerMode;
  isActive?: boolean;
  audioLevel?: number;
  color?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function VoiceVisualizer({
  mode = 'bars',
  isActive = false,
  audioLevel = 0,
  color = 'primary',
  className,
  size = 'md',
}: VoiceVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const [bars, setBars] = useState<number[]>(Array(12).fill(0.2));

  const sizeClasses = {
    sm: 'w-24 h-16',
    md: 'w-40 h-24',
    lg: 'w-64 h-40',
  };

  const colorClasses = {
    primary: 'bg-primary-500',
    secondary: 'bg-secondary-500',
    accent: 'bg-accent-500',
  };

  // Bars visualizer
  useEffect(() => {
    if (mode !== 'bars') return;

    const interval = setInterval(() => {
      if (isActive) {
        setBars((prev) =>
          prev.map(() => {
            const base = audioLevel > 0 ? audioLevel : 0.3;
            return Math.min(1, base + Math.random() * 0.5);
          })
        );
      } else {
        setBars((prev) => prev.map(() => 0.15 + Math.random() * 0.1));
      }
    }, 100);

    return () => clearInterval(interval);
  }, [mode, isActive, audioLevel]);

  // Circular visualizer
  useEffect(() => {
    if (mode !== 'circular') return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const baseRadius = Math.min(centerX, centerY) * 0.4;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw pulse rings
      if (isActive) {
        for (let i = 0; i < 3; i++) {
          const progress = ((Date.now() / 1000 + i * 0.3) % 1.5) / 1.5;
          const radius = baseRadius + progress * baseRadius * 0.8;
          const opacity = 1 - progress;

          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(139, 92, 246, ${opacity * 0.5})`;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      }

      // Draw center circle
      const currentRadius = baseRadius + (isActive ? audioLevel * 20 : 0);
      
      // Gradient fill
      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        currentRadius
      );
      gradient.addColorStop(0, 'rgba(139, 92, 246, 0.8)');
      gradient.addColorStop(1, 'rgba(6, 182, 212, 0.6)');

      ctx.beginPath();
      ctx.arc(centerX, centerY, currentRadius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Draw waveform around circle
      if (isActive) {
        ctx.beginPath();
        for (let i = 0; i <= 360; i += 5) {
          const angle = (i * Math.PI) / 180;
          const wave = Math.sin(angle * 6 + Date.now() / 200) * audioLevel * 15;
          const r = currentRadius + wave + 5;
          const x = centerX + Math.cos(angle) * r;
          const y = centerY + Math.sin(angle) * r;

          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.closePath();
        ctx.strokeStyle = 'rgba(139, 92, 246, 0.6)';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [mode, isActive, audioLevel]);

  // Waveform visualizer
  useEffect(() => {
    if (mode !== 'waveform') return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let phase = 0;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const centerY = canvas.height / 2;
      const amplitude = isActive ? 20 + audioLevel * 30 : 10;

      // Draw multiple waves
      for (let w = 0; w < 3; w++) {
        ctx.beginPath();
        ctx.moveTo(0, centerY);

        for (let x = 0; x < canvas.width; x++) {
          const y =
            centerY +
            Math.sin((x / 30) + phase + w * 0.5) * amplitude * (1 - w * 0.2) +
            Math.sin((x / 15) + phase * 2) * amplitude * 0.3;
          ctx.lineTo(x, y);
        }

        const opacity = 0.6 - w * 0.15;
        ctx.strokeStyle = `rgba(139, 92, 246, ${opacity})`;
        ctx.lineWidth = 3 - w;
        ctx.stroke();
      }

      phase += isActive ? 0.1 : 0.02;
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [mode, isActive, audioLevel]);

  if (mode === 'bars') {
    return (
      <div className={cn('flex items-end justify-center gap-1', sizeClasses[size], className)}>
        {bars.map((height, index) => (
          <div
            key={index}
            className={cn(
              'w-2 rounded-full transition-all duration-100',
              isActive ? colorClasses[color as keyof typeof colorClasses] : 'bg-muted-foreground/30'
            )}
            style={{
              height: `${height * 100}%`,
              transitionDelay: `${index * 20}ms`,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      width={mode === 'circular' ? 200 : 300}
      height={mode === 'circular' ? 200 : 100}
      className={cn(sizeClasses[size], className)}
    />
  );
}

// Animated microphone button
interface MicButtonProps {
  isRecording: boolean;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function MicButton({ isRecording, onClick, disabled, className, size = 'md' }: MicButtonProps) {
  const sizeClasses = {
    sm: 'w-10 h-10',
    md: 'w-16 h-16',
    lg: 'w-20 h-20',
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'relative rounded-full flex items-center justify-center transition-all duration-300',
        sizeClasses[size],
        isRecording
          ? 'bg-error-500 hover:bg-error-600'
          : 'bg-primary-500 hover:bg-primary-600',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {/* Pulse rings when recording */}
      {isRecording && (
        <>
          <span className="absolute inset-0 rounded-full bg-error-500 animate-ping opacity-25" />
          <span className="absolute inset-0 rounded-full bg-error-500 animate-pulse opacity-50" />
        </>
      )}

      {/* Mic icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className={cn(iconSizes[size], 'text-white relative z-10')}
      >
        <path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25a3.75 3.75 0 11-7.5 0V4.5z" />
        <path d="M6 10.5a.75.75 0 01.75.75v1.5a5.25 5.25 0 1010.5 0v-1.5a.75.75 0 011.5 0v1.5a6.751 6.751 0 01-6 6.709v2.291h3a.75.75 0 010 1.5h-7.5a.75.75 0 010-1.5h3v-2.291a6.751 6.751 0 01-6-6.709v-1.5A.75.75 0 016 10.5z" />
      </svg>
    </button>
  );
}

// AI thinking dots
interface AIThinkingDotsProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function AIThinkingDots({ className, size = 'md' }: AIThinkingDotsProps) {
  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
  };

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={cn(sizeClasses[size], 'rounded-full bg-primary-500 ai-thinking-dot')}
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}
