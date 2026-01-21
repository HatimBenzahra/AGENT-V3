'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Chip,
  LinearProgress,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ActivityFeed } from './ActivityFeed';
import { PlanDisplay } from './PlanDisplay';
import {
  Message,
  ServerMessage,
  ClientMessage,
  ConnectionState,
  AgentStatus,
  Activity,
  ExecutionPlan,
} from '@/lib/types';
import { getWebSocketUrl } from '@/lib/api';

interface ChatContainerProps {
  sessionId: string | null;
  onMenuClick: () => void;
  onSessionCreated: (id: string) => void;
}

export function ChatContainer({ sessionId, onMenuClick, onSessionCreated }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [currentPlan, setCurrentPlan] = useState<ExecutionPlan | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');

  const messageIdCounter = useRef(0);
  const activityIdCounter = useRef(0);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);
  const connectedSessionRef = useRef<string | null>(null);
  const onSessionCreatedRef = useRef(onSessionCreated);

  useEffect(() => {
    onSessionCreatedRef.current = onSessionCreated;
  }, [onSessionCreated]);

  const generateMessageId = () => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  };

  const generateActivityId = () => {
    activityIdCounter.current += 1;
    return `act-${Date.now()}-${activityIdCounter.current}`;
  };

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    if (!mountedRef.current) return;
    setMessages((prev) => [
      ...prev,
      { ...message, id: generateMessageId(), timestamp: new Date() },
    ]);
  }, []);

  const addActivity = useCallback((activity: Omit<Activity, 'id' | 'timestamp'>) => {
    if (!mountedRef.current) return;
    const newActivity = { ...activity, id: generateActivityId(), timestamp: new Date() };
    setActivities((prev) => [...prev, newActivity]);
    return newActivity.id;
  }, []);

  const updateActivity = useCallback((id: string, updates: Partial<Activity>) => {
    if (!mountedRef.current) return;
    setActivities((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...updates } : a))
    );
  }, []);

  const connect = useCallback((targetSessionId: string | null) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && connectedSessionRef.current === targetSessionId) {
      return;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const url = getWebSocketUrl(targetSessionId || undefined);
    setConnectionState('connecting');
    connectedSessionRef.current = targetSessionId;

    const ws = new WebSocket(url);
    let currentActivityId: string | null = null;

    ws.onopen = () => {
      if (mountedRef.current) setConnectionState('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data: ServerMessage = JSON.parse(event.data);
        console.log('[WS] Received:', data.type, data);
        if (!mountedRef.current) return;

        switch (data.type) {
          case 'connected':
            break;

          case 'initializing':
            addMessage({ type: 'system', content: data.message || 'Starting session...' });
            break;

          case 'session_ready':
            connectedSessionRef.current = data.session_id;
            onSessionCreatedRef.current(data.session_id);
            break;

          case 'status':
            setAgentStatus(data.status);
            break;

          case 'plan_proposal':
            setCurrentPlan(data.plan);
            setAgentStatus('idle');
            break;

          case 'plan_updated':
            setCurrentPlan(data.plan);
            break;

          case 'plan_started':
            setCurrentPlan(data.plan);
            setAgentStatus('working');
            break;

          case 'activity':
            if (data.status === 'running') {
              currentActivityId = addActivity({
                type: data.activity_type,
                tool: data.tool,
                params: data.params,
                status: 'running',
              }) || null;
            } else if (currentActivityId) {
              updateActivity(currentActivityId, {
                status: data.status,
                result: data.result,
                error: data.error,
                fileCreated: data.file_created,
              });
              currentActivityId = null;
            }
            break;

          case 'action':
            currentActivityId = addActivity({
              type: 'tool',
              tool: data.tool,
              params: data.params,
              status: 'running',
            }) || null;
            break;

          case 'observation':
            if (currentActivityId) {
              updateActivity(currentActivityId, {
                status: 'completed',
                result: data.content,
                fileCreated: data.file_created,
              });
              currentActivityId = null;
            }
            break;

          case 'final_answer':
            setAgentStatus('idle');
            setActivities([]);
            addMessage({ type: 'assistant', content: data.content });
            break;

          case 'error':
            setAgentStatus('idle');
            addMessage({ type: 'system', content: `Error: ${data.message}` });
            break;

          case 'interrupted':
            setAgentStatus('idle');
            setActivities([]);
            addMessage({ type: 'system', content: 'Task interrupted' });
            break;

          case 'interrupting':
            addMessage({ type: 'system', content: 'Stopping...' });
            break;

          case 'complete':
            setAgentStatus('idle');
            setActivities([]);
            if (currentPlan) {
              setCurrentPlan({ ...currentPlan, status: 'completed' });
            }
            break;

          case 'processing':
            setAgentStatus('working');
            break;

          case 'thought':
            break;
        }
      } catch (error) {
        console.error('Parse error:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      if (mountedRef.current) setConnectionState('error');
    };

    ws.onclose = (event) => {
      console.log('[WS] Closed:', event.code, event.reason);
      if (mountedRef.current) setConnectionState('disconnected');
    };

    wsRef.current = ws;
  }, [addMessage, addActivity, updateActivity, currentPlan]);

  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Sending:', message);
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.error('[WS] Cannot send - not connected');
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const shouldConnect = sessionId !== connectedSessionRef.current || 
      (sessionId === null && wsRef.current === null);
    if (shouldConnect) {
      setMessages([]);
      setActivities([]);
      setCurrentPlan(null);
      setAgentStatus('idle');
      connect(sessionId);
    }
    return () => { mountedRef.current = false; };
  }, [sessionId, connect]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const handleSendMessage = (content: string) => {
    addMessage({ type: 'user', content });
    sendMessage({ type: 'chat', content });
  };

  const handleInterrupt = () => sendMessage({ type: 'interrupt' });

  const handleApprovePlan = () => {
    if (currentPlan) {
      setCurrentPlan({ ...currentPlan, status: 'approved' });
      sendMessage({ type: 'approve_plan' });
    }
  };

  const handleUpdatePlan = (plan: ExecutionPlan) => {
    setCurrentPlan(plan);
    sendMessage({ type: 'update_plan', plan });
  };

  const getConnectionColor = () => {
    switch (connectionState) {
      case 'connected': return 'success';
      case 'connecting': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const isWorking = agentStatus !== 'idle';
  const showPlan = currentPlan && currentPlan.status === 'pending';
  const showActivities = isWorking && activities.length > 0;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%' }}>
      <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar variant="dense">
          <IconButton edge="start" color="inherit" onClick={onMenuClick} sx={{ mr: 1 }}>
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Agent
          </Typography>

          <Chip
            label={connectionState}
            color={getConnectionColor()}
            size="small"
            sx={{ textTransform: 'capitalize' }}
          />
        </Toolbar>
        {isWorking && <LinearProgress color="primary" />}
      </AppBar>

      <Box sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <Box sx={{ flexGrow: 1, overflow: 'auto', minHeight: 0, p: 2 }}>
          <MessageList messages={messages} />
          
          {showPlan && (
            <PlanDisplay
              plan={currentPlan}
              onApprove={handleApprovePlan}
              onUpdate={handleUpdatePlan}
            />
          )}
          
          {showActivities && (
            <ActivityFeed activities={activities} status={agentStatus} />
          )}
        </Box>

        <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', flexShrink: 0 }}>
          <MessageInput
            onSend={handleSendMessage}
            onInterrupt={handleInterrupt}
            isProcessing={isWorking}
            disabled={connectionState !== 'connected'}
          />
        </Box>
      </Box>
    </Box>
  );
}
