'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Typography,
  Button,
  Divider,
  CircularProgress,
  Tooltip,
  Stack,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import ChatIcon from '@mui/icons-material/Chat';
import FolderIcon from '@mui/icons-material/Folder';
import { useSession } from '@/hooks/useSession';

interface SessionListProps {
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string | null) => void;
  onNewSession: () => void;
}

export function SessionList({
  currentSessionId,
  onSessionSelect,
  onNewSession,
}: SessionListProps) {
  const { sessions, isLoading, error, refreshSessions, deleteSession } = useSession();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletingId(sessionId);
    await deleteSession(sessionId);
    setDeletingId(null);
    if (currentSessionId === sessionId) {
      onSessionSelect(null);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight={600}>
            Sessions
          </Typography>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={refreshSessions} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onNewSession}
        >
          New Session
        </Button>
      </Box>

      {/* Session List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {isLoading && sessions.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : error ? (
          <Box sx={{ p: 2 }}>
            <Typography color="error" variant="body2">
              {error}
            </Typography>
          </Box>
        ) : sessions.length === 0 ? (
          <Box sx={{ p: 2, textAlign: 'center' }}>
            <Typography color="text.secondary" variant="body2">
              No sessions yet
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            {sessions.map((session) => (
              <ListItem key={session.session_id} disablePadding>
                <ListItemButton
                  selected={currentSessionId === session.session_id}
                  onClick={() => onSessionSelect(session.session_id)}
                  sx={{
                    '&.Mui-selected': {
                      bgcolor: 'primary.dark',
                      '&:hover': {
                        bgcolor: 'primary.dark',
                      },
                    },
                  }}
                >
                  <ListItemText
                    primary={
                      <Typography variant="body2" fontWeight={500} noWrap>
                        {session.session_id}
                      </Typography>
                    }
                    secondary={
                      <Stack direction="row" spacing={1} alignItems="center" mt={0.5}>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <ChatIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                          <Typography variant="caption" color="text.secondary">
                            {session.message_count}
                          </Typography>
                        </Stack>
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <FolderIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                          <Typography variant="caption" color="text.secondary">
                            {session.file_count}
                          </Typography>
                        </Stack>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(session.updated_at)}
                        </Typography>
                      </Stack>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="Delete session">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(e) => handleDelete(session.session_id, e)}
                        disabled={deletingId === session.session_id}
                      >
                        {deletingId === session.session_id ? (
                          <CircularProgress size={16} />
                        ) : (
                          <DeleteIcon fontSize="small" />
                        )}
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </Box>

      {/* Footer */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary">
          {sessions.length} session{sessions.length !== 1 ? 's' : ''}
        </Typography>
      </Box>
    </Box>
  );
}
