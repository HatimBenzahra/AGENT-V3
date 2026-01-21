'use client';

import { useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Stack,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { TerminalSession } from '@/lib/types';

interface TerminalPanelProps {
  sessions: TerminalSession[];
  activeIndex: number;
  onNavigate: (index: number) => void;
  onClose: () => void;
}

export function TerminalPanel({
  sessions,
  activeIndex,
  onNavigate,
  onClose,
}: TerminalPanelProps) {
  const outputRef = useRef<HTMLPreElement>(null);
  const activeSession = sessions[activeIndex];

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [activeSession?.output]);

  if (!activeSession) return null;

  const canGoPrev = activeIndex > 0;
  const canGoNext = activeIndex < sessions.length - 1;

  return (
    <Paper
      sx={{
        width: '40%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderLeft: 1,
        borderColor: 'divider',
        bgcolor: '#1e1e1e',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 1,
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: '#252526',
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <IconButton
            size="small"
            onClick={() => onNavigate(activeIndex - 1)}
            disabled={!canGoPrev}
            sx={{ color: 'grey.400' }}
          >
            <ChevronLeftIcon fontSize="small" />
          </IconButton>
          <Typography variant="caption" sx={{ color: 'grey.400' }}>
            {activeIndex + 1} / {sessions.length}
          </Typography>
          <IconButton
            size="small"
            onClick={() => onNavigate(activeIndex + 1)}
            disabled={!canGoNext}
            sx={{ color: 'grey.400' }}
          >
            <ChevronRightIcon fontSize="small" />
          </IconButton>
        </Stack>

        <IconButton size="small" onClick={onClose} sx={{ color: 'grey.400' }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box sx={{ p: 1, bgcolor: '#2d2d2d', borderBottom: 1, borderColor: 'divider' }}>
        <Typography
          variant="body2"
          sx={{
            fontFamily: 'monospace',
            color: '#4ec9b0',
            fontSize: '0.85rem',
          }}
        >
          $ {activeSession.command}
        </Typography>
      </Box>

      <Box
        component="pre"
        ref={outputRef}
        sx={{
          flexGrow: 1,
          m: 0,
          p: 1.5,
          overflow: 'auto',
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          lineHeight: 1.5,
          color: '#d4d4d4',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}
      >
        {activeSession.output || 'Running...'}
      </Box>
    </Paper>
  );
}
