'use client';

import { useState, useCallback, useEffect } from 'react';
import { Session, SessionDetail } from '@/lib/types';
import { fetchSessions, fetchSession, deleteSession as apiDeleteSession } from '@/lib/api';

interface UseSessionReturn {
  sessions: Session[];
  currentSession: SessionDetail | null;
  isLoading: boolean;
  error: string | null;
  refreshSessions: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  clearCurrentSession: () => void;
}

export function useSession(): UseSessionReturn {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<SessionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSessions();
      setSessions(data.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sessions');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchSession(sessionId);
      setCurrentSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const deleteSession = useCallback(async (sessionId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await apiDeleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    } finally {
      setIsLoading(false);
    }
  }, [currentSession]);

  const clearCurrentSession = useCallback(() => {
    setCurrentSession(null);
  }, []);

  // Load sessions on mount
  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  return {
    sessions,
    currentSession,
    isLoading,
    error,
    refreshSessions,
    loadSession,
    deleteSession,
    clearCurrentSession,
  };
}
