'use client';

import { useState, useCallback } from 'react';

interface PipelineRunState {
  runId: string | null;
  isRunning: boolean;
  error: string | null;
}

export function usePipelineRun() {
  const [state, setState] = useState<PipelineRunState>({ runId: null, isRunning: false, error: null });

  const startPipeline = useCallback(async () => {
    setState({ runId: null, isRunning: true, error: null });
    try {
      const res = await fetch('/api/v1/agents/pipeline/run', { method: 'POST', credentials: 'include' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setState({ runId: data.run_id, isRunning: true, error: null });
    } catch (err) {
      setState({ runId: null, isRunning: false, error: err instanceof Error ? err.message : 'Failed to start pipeline' });
    }
  }, []);

  const handleComplete = useCallback(() => setState((prev) => ({ ...prev, isRunning: false })), []);
  const handleError = useCallback((msg: string) => setState((prev) => ({ ...prev, isRunning: false, error: msg })), []);
  const reset = useCallback(() => setState({ runId: null, isRunning: false, error: null }), []);

  return { runId: state.runId, isRunning: state.isRunning, error: state.error, startPipeline, handleComplete, handleError, reset };
}
