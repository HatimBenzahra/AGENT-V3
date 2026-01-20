'use client';

import { useState, useCallback } from 'react';
import { AgentState } from '@/lib/types';

interface UseAgentReturn {
  state: AgentState;
  setProcessing: (isProcessing: boolean) => void;
  setCurrentTask: (task: string | null) => void;
  setCurrentThought: (thought: string | null) => void;
  setCurrentTool: (tool: string | null) => void;
  reset: () => void;
}

const initialState: AgentState = {
  isProcessing: false,
  currentTask: null,
  currentThought: null,
  currentTool: null,
};

export function useAgent(): UseAgentReturn {
  const [state, setState] = useState<AgentState>(initialState);

  const setProcessing = useCallback((isProcessing: boolean) => {
    setState((prev) => ({ ...prev, isProcessing }));
  }, []);

  const setCurrentTask = useCallback((currentTask: string | null) => {
    setState((prev) => ({ ...prev, currentTask }));
  }, []);

  const setCurrentThought = useCallback((currentThought: string | null) => {
    setState((prev) => ({ ...prev, currentThought }));
  }, []);

  const setCurrentTool = useCallback((currentTool: string | null) => {
    setState((prev) => ({ ...prev, currentTool }));
  }, []);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  return {
    state,
    setProcessing,
    setCurrentTask,
    setCurrentThought,
    setCurrentTool,
    reset,
  };
}
