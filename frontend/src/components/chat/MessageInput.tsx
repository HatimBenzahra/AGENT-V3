'use client';

import { useState, KeyboardEvent } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Button,
  Tooltip,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import StopIcon from '@mui/icons-material/Stop';

interface MessageInputProps {
  onSend: (content: string) => void;
  onInterrupt: () => void;
  isProcessing: boolean;
  disabled: boolean;
}

export function MessageInput({ onSend, onInterrupt, isProcessing, disabled }: MessageInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim() && !isProcessing && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
      <TextField
        fullWidth
        multiline
        maxRows={4}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? 'Connecting...' : 'Ask me anything...'}
        disabled={disabled || isProcessing}
        variant="outlined"
        size="small"
        sx={{
          '& .MuiOutlinedInput-root': {
            bgcolor: 'background.paper',
          },
        }}
      />

      {isProcessing ? (
        <Tooltip title="Stop generation">
          <Button
            variant="contained"
            color="error"
            onClick={onInterrupt}
            sx={{ minWidth: 48, height: 40 }}
          >
            <StopIcon />
          </Button>
        </Tooltip>
      ) : (
        <Tooltip title="Send message">
          <span>
            <IconButton
              color="primary"
              onClick={handleSend}
              disabled={!input.trim() || disabled}
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                '&:hover': { bgcolor: 'primary.dark' },
                '&:disabled': { bgcolor: 'action.disabledBackground' },
              }}
            >
              <SendIcon />
            </IconButton>
          </span>
        </Tooltip>
      )}
    </Box>
  );
}
