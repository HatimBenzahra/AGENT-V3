'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Tooltip,
  Collapse,
  CircularProgress,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import LockIcon from '@mui/icons-material/Lock';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import RefreshIcon from '@mui/icons-material/Refresh';
import { listFiles } from '@/lib/api';
import { FileInfo } from '@/lib/types';

interface SessionInfoProps {
  sessionId: string;
}

export function SessionInfo({ sessionId }: SessionInfoProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFiles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listFiles(sessionId);
      setFiles(data.files);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [sessionId]);

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  return (
    <Paper sx={{ p: 2, bgcolor: 'background.paper' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
        <Stack direction="row" spacing={1} alignItems="center">
          <FolderIcon color="primary" fontSize="small" />
          <Typography variant="subtitle2">Workspace Files</Typography>
          <Chip label={files.length} size="small" />
        </Stack>
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Refresh">
            <IconButton size="small" onClick={loadFiles} disabled={isLoading}>
              {isLoading ? <CircularProgress size={16} /> : <RefreshIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Stack>
      </Stack>

      <Collapse in={expanded}>
        {error ? (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        ) : files.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No files in workspace
          </Typography>
        ) : (
          <List dense sx={{ maxHeight: 200, overflow: 'auto' }}>
            {files.map((file) => (
              <ListItem key={file.path} sx={{ py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {file.is_directory ? (
                    <FolderIcon fontSize="small" color="primary" />
                  ) : (
                    <InsertDriveFileIcon fontSize="small" />
                  )}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography variant="body2" noWrap>
                      {file.name}
                    </Typography>
                  }
                  secondary={
                    !file.is_directory && (
                      <Typography variant="caption" color="text.secondary">
                        {formatSize(file.size)}
                      </Typography>
                    )
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Collapse>
    </Paper>
  );
}
