'use client';

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  Chip,
  Stack,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PsychologyIcon from '@mui/icons-material/Psychology';
import BuildIcon from '@mui/icons-material/Build';
import VisibilityIcon from '@mui/icons-material/Visibility';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import InfoIcon from '@mui/icons-material/Info';
import { Message as MessageType } from '@/lib/types';
import { TerminalOutput } from '@/components/agent/TerminalOutput';
import { FilePreview } from '@/components/agent/FilePreview';

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
  const [expanded, setExpanded] = useState(true);

  const renderContent = () => {
    switch (message.type) {
      case 'user':
        return (
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Paper
              sx={{
                p: 2,
                maxWidth: '80%',
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
              }}
            >
              <Stack direction="row" spacing={1} alignItems="flex-start">
                <PersonIcon fontSize="small" />
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {message.content}
                </Typography>
              </Stack>
            </Paper>
          </Box>
        );

      case 'thought':
        return (
          <Paper
            sx={{
              p: 2,
              bgcolor: 'rgba(99, 102, 241, 0.1)',
              border: '1px solid',
              borderColor: 'primary.dark',
            }}
          >
            <Stack direction="row" spacing={1} alignItems="center" mb={1}>
              <PsychologyIcon color="primary" fontSize="small" />
              <Typography variant="subtitle2" color="primary">
                Thinking
              </Typography>
              <IconButton size="small" onClick={() => setExpanded(!expanded)}>
                {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Stack>
            <Collapse in={expanded}>
              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap', pl: 4 }}>
                {message.content}
              </Typography>
            </Collapse>
          </Paper>
        );

      case 'action':
        return (
          <Paper
            sx={{
              p: 2,
              bgcolor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid',
              borderColor: 'secondary.dark',
            }}
          >
            <Stack direction="row" spacing={1} alignItems="center">
              <BuildIcon color="secondary" fontSize="small" />
              <Typography variant="subtitle2" color="secondary">
                Action
              </Typography>
              <Chip
                label={message.tool}
                size="small"
                color="secondary"
                variant="outlined"
              />
            </Stack>
            {message.params && Object.keys(message.params).length > 0 && (
              <Box sx={{ mt: 1, pl: 4 }}>
                <Typography variant="caption" color="text.secondary" component="pre" sx={{ fontFamily: 'monospace' }}>
                  {JSON.stringify(message.params, null, 2)}
                </Typography>
              </Box>
            )}
          </Paper>
        );

      case 'observation':
        const isTerminal = message.tool === 'execute_command';
        const isFileWrite = message.tool === 'write_file' && message.fileCreated;

        return (
          <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
            <Stack direction="row" spacing={1} alignItems="center" mb={1}>
              <VisibilityIcon fontSize="small" sx={{ color: 'info.main' }} />
              <Typography variant="subtitle2" color="info.main">
                Observation
              </Typography>
              {message.tool && (
                <Chip label={message.tool} size="small" variant="outlined" />
              )}
              <IconButton size="small" onClick={() => setExpanded(!expanded)}>
                {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Stack>
            <Collapse in={expanded}>
              {isTerminal ? (
                <TerminalOutput content={message.content} />
              ) : isFileWrite && message.fileCreated ? (
                <FilePreview
                  path={message.fileCreated.path}
                  content={message.fileCreated.content}
                />
              ) : (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ whiteSpace: 'pre-wrap', pl: 4, fontFamily: 'monospace', fontSize: '0.8rem' }}
                >
                  {message.content}
                </Typography>
              )}
            </Collapse>
          </Paper>
        );

      case 'final_answer':
        return (
          <Paper
            sx={{
              p: 2,
              bgcolor: 'rgba(16, 185, 129, 0.15)',
              border: '2px solid',
              borderColor: 'success.main',
            }}
          >
            <Stack direction="row" spacing={1} alignItems="center" mb={1}>
              <CheckCircleIcon color="success" />
              <Typography variant="subtitle1" color="success.main" fontWeight={600}>
                Answer
              </Typography>
            </Stack>
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', pl: 4 }}>
              {message.content}
            </Typography>
          </Paper>
        );

      case 'error':
        return (
          <Paper
            sx={{
              p: 2,
              bgcolor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid',
              borderColor: 'error.main',
            }}
          >
            <Stack direction="row" spacing={1} alignItems="center">
              <ErrorIcon color="error" />
              <Typography variant="body2" color="error">
                {message.content}
              </Typography>
            </Stack>
          </Paper>
        );

      case 'system':
        return (
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <Chip
              icon={<InfoIcon />}
              label={message.content}
              size="small"
              variant="outlined"
              sx={{ color: 'text.secondary' }}
            />
          </Box>
        );

      default:
        return null;
    }
  };

  return <Box>{renderContent()}</Box>;
}
