'use client';

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Stack,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import TerminalIcon from '@mui/icons-material/Terminal';

interface TerminalOutputProps {
  content: string;
  title?: string;
}

export function TerminalOutput({ content, title = 'Terminal' }: TerminalOutputProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Parse exit code if present
  const exitCodeMatch = content.match(/Exit code: (\d+)/);
  const exitCode = exitCodeMatch ? parseInt(exitCodeMatch[1]) : null;
  const isSuccess = exitCode === 0;

  return (
    <Paper
      sx={{
        bgcolor: '#1a1a2e',
        borderRadius: 2,
        overflow: 'hidden',
        border: '1px solid',
        borderColor: exitCode !== null ? (isSuccess ? 'success.dark' : 'error.dark') : 'divider',
      }}
    >
      {/* Terminal Header */}
      <Box
        sx={{
          px: 2,
          py: 1,
          bgcolor: '#16162a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          <TerminalIcon fontSize="small" sx={{ color: 'text.secondary' }} />
          <Typography variant="caption" color="text.secondary">
            {title}
          </Typography>
          {exitCode !== null && (
            <Typography
              variant="caption"
              sx={{
                px: 1,
                py: 0.25,
                borderRadius: 1,
                bgcolor: isSuccess ? 'success.dark' : 'error.dark',
                color: 'white',
              }}
            >
              Exit: {exitCode}
            </Typography>
          )}
        </Stack>
        <Tooltip title={copied ? 'Copied!' : 'Copy'}>
          <IconButton size="small" onClick={handleCopy}>
            {copied ? (
              <CheckIcon fontSize="small" color="success" />
            ) : (
              <ContentCopyIcon fontSize="small" sx={{ color: 'text.secondary' }} />
            )}
          </IconButton>
        </Tooltip>
      </Box>

      {/* Terminal Content */}
      <Box
        sx={{
          p: 2,
          maxHeight: 400,
          overflowY: 'auto',
          '&::-webkit-scrollbar': {
            width: 8,
          },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: 'rgba(255,255,255,0.2)',
            borderRadius: 4,
          },
        }}
      >
        <Typography
          component="pre"
          sx={{
            fontFamily: '"Fira Code", "Consolas", monospace',
            fontSize: '0.8rem',
            lineHeight: 1.6,
            color: '#e2e8f0',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            m: 0,
          }}
        >
          {content}
        </Typography>
      </Box>
    </Paper>
  );
}
