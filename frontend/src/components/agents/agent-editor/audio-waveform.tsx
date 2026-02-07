'use client';

import { cn } from '@/lib/utils';
import { useRef, useEffect, useState } from 'react';
import { Mic, Volume2 } from 'lucide-react';

interface AudioWaveformProps {
  isActive?: boolean;
  isUserSpeaking?: boolean;
  isAgentSpeaking?: boolean;
  className?: string;
}

function drawWaveform(
  canvas: HTMLCanvasElement,
  isSpeaking: boolean,
  color: string,
  frameRef: { current: number }
) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const width = canvas.width;
  const height = canvas.height;
  const centerY = height / 2;

  // Clear canvas
  ctx.clearRect(0, 0, width, height);

  // Draw center line
  ctx.strokeStyle = 'rgba(100, 100, 100, 0.3)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, centerY);
  ctx.lineTo(width, centerY);
  ctx.stroke();

  if (!isSpeaking) {
    // Draw flat line when not speaking
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();
    ctx.globalAlpha = 1;
    return;
  }

  // Generate dynamic waveform when speaking
  const frame = frameRef.current;
  const numBars = 64;
  const barWidth = width / numBars;
  
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.8;

  for (let i = 0; i < numBars; i++) {
    // Create organic-looking amplitude using multiple sine waves
    const t = frame * 0.15;
    const amplitude = (
      Math.sin(t + i * 0.3) * 0.3 +
      Math.sin(t * 1.5 + i * 0.2) * 0.25 +
      Math.sin(t * 0.7 + i * 0.5) * 0.2 +
      Math.random() * 0.15
    );
    
    const barHeight = Math.abs(amplitude) * height * 0.7;
    const x = i * barWidth;
    const y = centerY - barHeight / 2;
    
    // Draw rounded bar
    const radius = barWidth / 3;
    ctx.beginPath();
    ctx.roundRect(x + 1, y, barWidth - 2, barHeight, radius);
    ctx.fill();
  }
  
  ctx.globalAlpha = 1;

  // Draw glow effect
  ctx.shadowColor = color;
  ctx.shadowBlur = 15;
  ctx.beginPath();
  ctx.moveTo(0, centerY);
  for (let i = 0; i < width; i += 4) {
    const t = frame * 0.1;
    const y = centerY + Math.sin(t + i * 0.05) * 10 * (0.5 + Math.random() * 0.5);
    ctx.lineTo(i, y);
  }
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.shadowBlur = 0;
}

function WaveformCanvas({ 
  isSpeaking,
  color,
  label,
  icon: Icon,
}: { 
  isSpeaking: boolean;
  color: string;
  label: string;
  icon: typeof Mic;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const updateDimensions = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const animate = () => {
      frameRef.current++;
      drawWaveform(canvas, isSpeaking, color, frameRef);
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isSpeaking, color]);

  return (
    <div className="flex-1 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div 
          className={cn(
            'flex h-6 w-6 items-center justify-center rounded-full transition-all',
            isSpeaking ? 'animate-pulse' : ''
          )}
          style={{ backgroundColor: `${color}20` }}
        >
          <Icon className="h-3 w-3" style={{ color }} />
        </div>
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        {isSpeaking && (
          <span 
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: color }}
          />
        )}
      </div>
      <div className="relative h-16 rounded-lg bg-muted/30 overflow-hidden">
        <canvas 
          ref={canvasRef} 
          className="absolute inset-0 w-full h-full"
        />
      </div>
    </div>
  );
}

export function AudioWaveform({ 
  isActive = false,
  isUserSpeaking = false,
  isAgentSpeaking = false,
  className 
}: AudioWaveformProps) {
  // Unified speaking state - either customer or agent speaking triggers animation
  const isSpeaking = isUserSpeaking || isAgentSpeaking;
  
  // Dynamic color based on who is speaking
  const getColor = () => {
    if (isUserSpeaking && isAgentSpeaking) return '#8b5cf6'; // purple when both
    if (isUserSpeaking) return '#3b82f6'; // blue for customer
    if (isAgentSpeaking) return '#10b981'; // green for agent
    return '#6b7280'; // gray when silent
  };

  return (
    <div className={cn('rounded-xl border border-border bg-card p-4', className)}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm">Audio Visualization</h3>
        {isActive && (
          <span className="flex items-center gap-1.5 text-xs text-green-500">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Live
          </span>
        )}
      </div>
      
      {/* Single unified waveform */}
      <WaveformCanvas 
        isSpeaking={isSpeaking}
        color={getColor()}
        label={isUserSpeaking ? 'Customer' : isAgentSpeaking ? 'Agent' : 'Waiting'}
        icon={isUserSpeaking ? Mic : Volume2}
      />
      
      {/* Speaking indicator */}
      <div className="flex items-center justify-center gap-4 mt-4 pt-4 border-t border-border">
        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
          isUserSpeaking 
            ? 'bg-blue-500/20 text-blue-500' 
            : 'bg-muted text-muted-foreground'
        )}>
          <Mic className="h-3 w-3" />
          {isUserSpeaking ? 'Customer Speaking' : 'Customer Silent'}
        </div>
        <div className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
          isAgentSpeaking 
            ? 'bg-green-500/20 text-green-500' 
            : 'bg-muted text-muted-foreground'
        )}>
          <Volume2 className="h-3 w-3" />
          {isAgentSpeaking ? 'Agent Speaking' : 'Agent Silent'}
        </div>
      </div>
    </div>
  );
}
