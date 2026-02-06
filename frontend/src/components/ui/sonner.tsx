'use client';

import { Toaster as SonnerToaster, ToasterProps } from 'sonner';
import { useTheme } from 'next-themes';

type Props = Omit<ToasterProps, 'theme'>;

export function Toaster(props: Props) {
  const { theme } = useTheme();

  return (
    <SonnerToaster
      theme={theme as 'light' | 'dark' | 'system'}
      position="top-right"
      toastOptions={{
        style: {
          background: 'hsl(var(--card))',
          border: '1px solid hsl(var(--border))',
          color: 'hsl(var(--foreground))',
        },
      }}
      {...props}
    />
  );
}
