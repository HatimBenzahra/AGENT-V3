'use client';

import { useRef, useEffect } from 'react';
import { Box, Paper, Typography, Avatar } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import InfoIcon from '@mui/icons-material/Info';
import ReactMarkdown from 'react-markdown';
import { Message } from '@/lib/types';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          color: 'text.secondary',
          textAlign: 'center',
          p: 4,
        }}
      >
        <SmartToyIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
        <Typography variant="h5" gutterBottom>
          Hello! How can I help you?
        </Typography>
        <Typography variant="body2" sx={{ maxWidth: 400, opacity: 0.7 }}>
          I can help with coding, file operations, web searches, document creation, and more.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      <div ref={endRef} />
    </Box>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';

  if (isSystem) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
        <Typography
          variant="caption"
          sx={{
            color: 'text.secondary',
            bgcolor: 'action.hover',
            px: 2,
            py: 0.5,
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
          }}
        >
          <InfoIcon sx={{ fontSize: 14 }} />
          {message.content}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1.5,
        flexDirection: isUser ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
      }}
    >
      <Avatar
        sx={{
          width: 32,
          height: 32,
          bgcolor: isUser ? 'primary.main' : 'secondary.main',
        }}
      >
        {isUser ? <PersonIcon sx={{ fontSize: 18 }} /> : <SmartToyIcon sx={{ fontSize: 18 }} />}
      </Avatar>

      <Paper
        elevation={0}
        sx={{
          p: 2,
          maxWidth: '75%',
          bgcolor: isUser ? 'primary.main' : 'background.paper',
          color: isUser ? 'primary.contrastText' : 'text.primary',
          borderRadius: 2,
          border: isUser ? 'none' : '1px solid',
          borderColor: 'divider',
        }}
      >
        {isUser ? (
          <Typography variant="body1">{message.content}</Typography>
        ) : (
          <Box
            sx={{
              '& p': { m: 0, mb: 1, '&:last-child': { mb: 0 } },
              '& pre': {
                bgcolor: 'grey.900',
                color: 'grey.100',
                p: 1.5,
                borderRadius: 1,
                overflow: 'auto',
                fontSize: '0.85rem',
              },
              '& code': {
                bgcolor: 'action.hover',
                px: 0.5,
                borderRadius: 0.5,
                fontSize: '0.9em',
              },
              '& pre code': {
                bgcolor: 'transparent',
                p: 0,
              },
              '& ul, & ol': { pl: 2, my: 1 },
              '& a': { color: 'primary.main' },
            }}
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </Box>
        )}
      </Paper>
    </Box>
  );
}
