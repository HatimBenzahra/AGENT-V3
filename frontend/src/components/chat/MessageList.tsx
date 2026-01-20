'use client';

import { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import { Message as MessageType } from '@/lib/types';
import { Message } from './Message';
import { ThinkingIndicator } from '@/components/agent/ThinkingIndicator';

interface MessageListProps {
  messages: MessageType[];
  currentThought: string | null;
  isProcessing: boolean;
}

export function MessageList({ messages, currentThought, isProcessing }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentThought]);

  if (messages.length === 0 && !isProcessing) {
    return (
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: 4,
        }}
      >
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
          Welcome to ReAct Agent
        </Typography>
        <Typography variant="body1" color="text.secondary" textAlign="center" maxWidth={500}>
          I can help you with coding tasks, file operations, web searches, and more.
          Try asking me to create a script, search the web, or execute commands.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: '100%',
        overflowY: 'auto',
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}
    >
      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}

      {isProcessing && <ThinkingIndicator thought={currentThought} />}

      <div ref={bottomRef} />
    </Box>
  );
}
