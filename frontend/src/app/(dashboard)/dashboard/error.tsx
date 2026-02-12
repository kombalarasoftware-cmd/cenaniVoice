'use client';

import { useEffect } from 'react';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Dashboard error:', error);
  }, [error]);

  return (
    <div className="flex h-[60vh] items-center justify-center">
      <div className="mx-auto max-w-md rounded-xl border border-white/10 bg-white/5 p-8 text-center backdrop-blur-xl">
        <h2 className="mb-2 text-xl font-semibold text-white">Page Error</h2>
        <p className="mb-6 text-sm text-zinc-400">
          This page encountered an error. Your other pages still work normally.
        </p>
        <button
          onClick={reset}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
        >
          Reload page
        </button>
      </div>
    </div>
  );
}
