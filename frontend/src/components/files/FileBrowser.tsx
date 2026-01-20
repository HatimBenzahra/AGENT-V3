'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Chip,
  Tooltip,
  CircularProgress,
  Stack,
  Button,
  LinearProgress,
} from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import ImageIcon from '@mui/icons-material/Image';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CodeIcon from '@mui/icons-material/Code';
import DescriptionIcon from '@mui/icons-material/Description';
import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';
import CloseIcon from '@mui/icons-material/Close';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import SyncIcon from '@mui/icons-material/Sync';
import { listFiles } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const AUTO_REFRESH_INTERVAL = 3000; // 3 seconds

interface FileInfo {
  name: string;
  path: string;
  size: number;
  is_directory: boolean;
}

interface FileBrowserProps {
  sessionId: string | null;
  onFileSelect: (file: FileInfo) => void;
  onClose: () => void;
}

function getFileIcon(name: string, isDirectory: boolean) {
  if (isDirectory) return <FolderIcon sx={{ color: '#f9e2af' }} />;
  
  const ext = name.split('.').pop()?.toLowerCase() || '';
  
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) {
    return <ImageIcon sx={{ color: '#89dceb' }} />;
  }
  if (ext === 'pdf') {
    return <PictureAsPdfIcon sx={{ color: '#f38ba8' }} />;
  }
  if (['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'sh'].includes(ext)) {
    return <CodeIcon sx={{ color: '#a6e3a1' }} />;
  }
  if (['md', 'txt', 'log'].includes(ext)) {
    return <DescriptionIcon sx={{ color: '#cba6f7' }} />;
  }
  return <InsertDriveFileIcon sx={{ color: '#9399b2' }} />;
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function FileBrowser({ sessionId, onFileSelect, onClose }: FileBrowserProps) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadFiles = useCallback(async (showLoading = true) => {
    if (!sessionId) return;
    
    if (showLoading) setLoading(true);
    setError(null);
    
    try {
      const response = await listFiles(sessionId, currentPath);
      setFiles(response.files || []);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to load files:', err);
      // Don't show error for background refreshes
      if (showLoading) {
        setError('Failed to load files');
      }
      setFiles([]);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [sessionId, currentPath]);

  // Initial load and path changes
  useEffect(() => {
    loadFiles(true);
  }, [sessionId, currentPath, loadFiles]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefresh && sessionId) {
      refreshIntervalRef.current = setInterval(() => {
        loadFiles(false); // Silent refresh
      }, AUTO_REFRESH_INTERVAL);
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefresh, sessionId, loadFiles]);

  const handleFileClick = (file: FileInfo) => {
    if (file.is_directory) {
      setCurrentPath(file.path);
    } else {
      onFileSelect(file);
    }
  };

  const handleBack = () => {
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    setCurrentPath(parts.join('/'));
  };

  const handleDownload = (file: FileInfo, e: React.MouseEvent) => {
    e.stopPropagation();
    const url = `${API_BASE}/api/files/${sessionId}/download?path=${encodeURIComponent(file.path)}`;
    window.open(url, '_blank');
  };

  if (!sessionId) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <FolderOpenIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
        <Typography color="text.secondary">
          No session selected
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <FolderOpenIcon color="primary" />
            <Typography variant="subtitle1" fontWeight={600}>
              Files
            </Typography>
            {autoRefresh && (
              <Chip 
                icon={<SyncIcon sx={{ fontSize: 14 }} />} 
                label="Live" 
                size="small" 
                color="success" 
                variant="outlined"
                sx={{ height: 20, '& .MuiChip-label': { px: 0.5, fontSize: '0.7rem' } }}
              />
            )}
          </Stack>
          <Stack direction="row" spacing={0.5}>
            <Tooltip title={autoRefresh ? "Disable auto-refresh" : "Enable auto-refresh"}>
              <IconButton 
                size="small" 
                onClick={() => setAutoRefresh(!autoRefresh)}
                color={autoRefresh ? "primary" : "default"}
              >
                <SyncIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Refresh now">
              <IconButton size="small" onClick={() => loadFiles(true)}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Close">
              <IconButton size="small" onClick={onClose}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>
        {lastUpdate && (
          <Typography variant="caption" color="text.secondary">
            Updated: {lastUpdate.toLocaleTimeString()}
          </Typography>
        )}
      </Box>
      
      {/* Loading indicator for auto-refresh */}
      {loading && <LinearProgress sx={{ height: 2 }} />}

      {/* Breadcrumb */}
      {currentPath && (
        <Box sx={{ px: 2, py: 1, bgcolor: 'action.hover' }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Button size="small" onClick={handleBack} sx={{ minWidth: 'auto' }}>
              ← Back
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
              /{currentPath}
            </Typography>
          </Stack>
        </Box>
      )}

      {/* File List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress size={32} />
          </Box>
        ) : error ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="error">{error}</Typography>
            <Button onClick={() => loadFiles(true)} sx={{ mt: 1 }}>Retry</Button>
          </Box>
        ) : files.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <InsertDriveFileIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
            <Typography color="text.secondary">No files yet</Typography>
          </Box>
        ) : (
          <List dense disablePadding>
            {files.map((file) => (
              <ListItem
                key={file.path}
                disablePadding
                secondaryAction={
                  !file.is_directory && (
                    <Tooltip title="Download">
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={(e) => handleDownload(file, e)}
                      >
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              >
                <ListItemButton onClick={() => handleFileClick(file)}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {getFileIcon(file.name, file.is_directory)}
                  </ListItemIcon>
                  <ListItemText
                    primary={file.name}
                    secondary={!file.is_directory && formatSize(file.size)}
                    primaryTypographyProps={{
                      variant: 'body2',
                      noWrap: true,
                      sx: { fontFamily: file.is_directory ? 'inherit' : 'monospace' },
                    }}
                    secondaryTypographyProps={{
                      variant: 'caption',
                    }}
                  />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        )}
      </Box>

      {/* Footer */}
      <Box
        sx={{
          p: 1.5,
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'action.hover',
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {files.length} items • Session: {sessionId?.slice(0, 8)}
        </Typography>
      </Box>
    </Box>
  );
}
