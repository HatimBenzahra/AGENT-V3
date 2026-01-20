'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { ClientMessage, ServerMessage, ConnectionState } from '@/lib/types';
import { getWebSocketUrl } from '@/lib/api';

interface UseWebSocketOptions {
  sessionId?: string;
  onMessage: (message: ServerMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  sendMessage: (message: ClientMessage) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket({
  sessionId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectAttempts = 3,
  reconnectInterval = 2000,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);
  
  // Store callbacks in refs to avoid reconnection on callback changes
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);
  
  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  
  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);
  
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);
  
  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    // Clear any existing reconnect timeout
    clearReconnectTimeout();

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionState('connecting');
    shouldReconnectRef.current = true;
    reconnectCountRef.current = 0;

    const url = getWebSocketUrl(sessionId);
    console.log('Connecting to WebSocket:', url);
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnectionState('connected');
      reconnectCountRef.current = 0;
      onConnectRef.current?.();
    };

    ws.onmessage = (event) => {
      try {
        const data: ServerMessage = JSON.parse(event.data);
        onMessageRef.current(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setConnectionState('error');
      onErrorRef.current?.(event);
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      setConnectionState('disconnected');
      onDisconnectRef.current?.();

      // Attempt reconnect if should reconnect and haven't exceeded attempts
      if (shouldReconnectRef.current && reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current += 1;
        console.log(`Reconnecting... attempt ${reconnectCountRef.current}`);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      }
    };

    wsRef.current = ws;
  }, [sessionId, reconnectAttempts, reconnectInterval, clearReconnectTimeout]);

  const disconnect = useCallback(() => {
    console.log('Disconnecting WebSocket');
    shouldReconnectRef.current = false;
    clearReconnectTimeout();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionState('disconnected');
  }, [clearReconnectTimeout]);

  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('Sending message:', message);
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected, state:', wsRef.current?.readyState);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldReconnectRef.current = false;
      clearReconnectTimeout();
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [clearReconnectTimeout]);

  return {
    connectionState,
    sendMessage,
    connect,
    disconnect,
  };
}
