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
import { SuggestionPanel } from './SuggestionPanel';
import { Message, ServerMessage, ClientMessage, ConnectionState } from '@/lib/types';
import { getWebSocketUrl } from '@/lib/api';

interface ChatContainerProps {
  sessionId: string | null;
  onMenuClick: () => void;
  onSessionCreated: (id: string) => void;
}

export function ChatContainer({ sessionId, onMenuClick, onSessionCreated }: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentThought, setCurrentThought] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  
  const messageIdCounter = useRef(0);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);
  
  // Track the session we're actually connected to (not the prop)
  const connectedSessionRef = useRef<string | null>(null);
  const onSessionCreatedRef = useRef(onSessionCreated);
  
  // Update callback ref
  useEffect(() => {
    onSessionCreatedRef.current = onSessionCreated;
  }, [onSessionCreated]);

  const generateId = () => {
    messageIdCounter.current += 1;
    return `msg-${Date.now()}-${messageIdCounter.current}`;
  };

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    if (!mountedRef.current) return;
    setMessages((prev) => [
      ...prev,
      {
        ...message,
        id: generateId(),
        timestamp: new Date(),
      },
    ]);
  }, []);

  // Connect WebSocket - only call this when we actually want to connect
  const connect = useCallback((targetSessionId: string | null) => {
    // Don't reconnect if already connected to this session
    if (wsRef.current?.readyState === WebSocket.OPEN && connectedSessionRef.current === targetSessionId) {
      console.log('Already connected to this session');
      return;
    }
    
    // Close existing connection
    if (wsRef.current) {
      console.log('Closing existing connection');
      wsRef.current.close();
      wsRef.current = null;
    }

    const url = getWebSocketUrl(targetSessionId || undefined);
    console.log('Connecting to:', url);
    setConnectionState('connecting');
    connectedSessionRef.current = targetSessionId;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket opened');
      if (mountedRef.current) {
        setConnectionState('connected');
      }
    };

    ws.onmessage = (event) => {
      try {
        const data: ServerMessage = JSON.parse(event.data);
        console.log('Received message:', data.type);
        
        if (!mountedRef.current) return;
        
        switch (data.type) {
          case 'connected':
            console.log('Connected to session:', data.session_id);
            break;

          case 'initializing':
            setIsProcessing(true);
            addMessage({
              type: 'system',
              content: data.message || 'Initializing session...',
            });
            break;

          case 'session_ready':
            console.log('Session ready:', data.session_id);
            // Update our connected session ref - DON'T trigger reconnect
            connectedSessionRef.current = data.session_id;
            // Notify parent (this will update sessionId prop, but we won't reconnect)
            onSessionCreatedRef.current(data.session_id);
            addMessage({
              type: 'system',
              content: `Session ready: ${data.session_id}`,
            });
            break;

          case 'processing':
            setIsProcessing(true);
            setCurrentThought(null);
            break;

          case 'thought':
            setCurrentThought(data.content);
            addMessage({
              type: 'thought',
              content: data.content,
            });
            break;

          case 'action':
            addMessage({
              type: 'action',
              content: `Using ${data.tool}`,
              tool: data.tool,
              params: data.params,
            });
            break;

          case 'observation':
            addMessage({
              type: 'observation',
              content: data.content,
              tool: data.tool,
              fileCreated: data.file_created,
            });
            break;

          case 'final_answer':
            setIsProcessing(false);
            setCurrentThought(null);
            addMessage({
              type: 'final_answer',
              content: data.content,
            });
            break;

          case 'error':
            setIsProcessing(false);
            addMessage({
              type: 'error',
              content: data.message,
            });
            break;

          case 'interrupted':
            setIsProcessing(false);
            setCurrentThought(null);
            addMessage({
              type: 'system',
              content: 'Task interrupted by user',
            });
            break;

          case 'complete':
            setIsProcessing(false);
            setCurrentThought(null);
            break;
            
          case 'suggestion_received':
            addMessage({
              type: 'system',
              content: `Suggestion queued: "${data.content}"`,
            });
            break;
            
          case 'suggestion_applied':
            addMessage({
              type: 'system',
              content: `Suggestion applied: "${data.content}"`,
            });
            break;
            
          case 'recovery':
            addMessage({
              type: 'system',
              content: data.content || 'Self-healing in progress...',
            });
            break;
        }
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (mountedRef.current) {
        setConnectionState('error');
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code);
      if (mountedRef.current) {
        setConnectionState('disconnected');
      }
    };

    wsRef.current = ws;
  }, [addMessage]);

  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('Sending:', message);
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not open, state:', wsRef.current?.readyState);
    }
  }, []);

  // Connect on mount and when sessionId changes FROM USER ACTION (not from session_ready)
  useEffect(() => {
    mountedRef.current = true;
    
    // Only reconnect if the sessionId prop differs from what we're connected to
    // This prevents reconnection when session_ready updates the parent state
    if (sessionId !== connectedSessionRef.current) {
      console.log(`Session changed: ${connectedSessionRef.current} -> ${sessionId}, reconnecting...`);
      setMessages([]); // Clear messages on session change
      connect(sessionId);
    } else {
      console.log('Session unchanged, not reconnecting');
    }

    return () => {
      mountedRef.current = false;
    };
  }, [sessionId, connect]);

  // Cleanup on unmount only
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const handleSendMessage = (content: string) => {
    addMessage({
      type: 'user',
      content,
    });
    sendMessage({ type: 'chat', content });
  };

  const handleInterrupt = () => {
    sendMessage({ type: 'interrupt' });
  };

  const handleSuggestion = (suggestion: string) => {
    sendMessage({ type: 'suggestion', content: suggestion });
  };

  const getConnectionColor = () => {
    switch (connectionState) {
      case 'connected':
        return 'success';
      case 'connecting':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar>
          <IconButton edge="start" color="inherit" onClick={onMenuClick} sx={{ mr: 2 }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 600 }}>
            ReAct Agent
          </Typography>
          <Chip
            label={connectionState}
            color={getConnectionColor()}
            size="small"
            sx={{ textTransform: 'capitalize' }}
          />
        </Toolbar>
        {isProcessing && <LinearProgress color="primary" />}
      </AppBar>

      {/* Messages */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden', position: 'relative' }}>
        <MessageList
          messages={messages}
          currentThought={currentThought}
          isProcessing={isProcessing}
        />
        
        {/* Suggestion Panel - appears during processing */}
        <SuggestionPanel
          isProcessing={isProcessing}
          onSuggest={handleSuggestion}
          onInterrupt={handleInterrupt}
          currentThought={currentThought}
        />
      </Box>

      {/* Input */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <MessageInput
          onSend={handleSendMessage}
          onInterrupt={handleInterrupt}
          isProcessing={isProcessing}
          disabled={connectionState !== 'connected'}
        />
      </Box>
    </Box>
  );
}
