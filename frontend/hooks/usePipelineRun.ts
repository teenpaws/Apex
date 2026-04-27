'use client';

import { useState, useCallback } from 'react';
import axios from 'axios';
import { agentsApi } from '@/lib/api';

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
      const res = await agentsApi.runPipeline();
      setState({ runId: res.data.run_id, isRunning: true, error: null });
    } catch (err) {
      let msg = 'Failed to start pipeline';
      if (axios.isAxiosError(err)) {
        msg = err.response?.data?.error ?? err.response?.data?.detail ?? err.message;
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setState({ runId: null, isRunning: false, error: msg });
    }
  }, []);

  const handleComplete = useCallback(() => setState((prev) => ({ ...prev, isRunning: false })), []);
  const handleError = useCallback((msg: string) => setState((prev) => ({ ...prev, isRunning: false, error: msg })), []);
  const reset = useCallback(() => setState({ runId: null, isRunning: false, error: null }), []);

  return { runId: state.runId, isRunning: state.isRunning, error: state.error, startPipeline, handleComplete, handleError, reset };
}
