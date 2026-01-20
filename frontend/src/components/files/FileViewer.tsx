'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  IconButton,
  Button,
  CircularProgress,
  Stack,
  Chip,
  Paper,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DownloadIcon from '@mui/icons-material/Download';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ImageIcon from '@mui/icons-material/Image';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CodeIcon from '@mui/icons-material/Code';
import { readFile } from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FileViewerProps {
  sessionId: string;
  file: {
    name: string;
    path: string;
    size: number;
  } | null;
  onClose: () => void;
}

function getFileType(name: string): 'image' | 'pdf' | 'code' | 'text' {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
  if (ext === 'pdf') return 'pdf';
  if (['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'sh', 'sql', 'yml', 'yaml'].includes(ext)) return 'code';
  return 'text';
}

function getLanguage(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  const langMap: Record<string, string> = {
    py: 'Python',
    js: 'JavaScript',
    ts: 'TypeScript',
    jsx: 'React JSX',
    tsx: 'React TSX',
    json: 'JSON',
    md: 'Markdown',
    html: 'HTML',
    css: 'CSS',
    sh: 'Shell',
    sql: 'SQL',
    yml: 'YAML',
    yaml: 'YAML',
  };
  return langMap[ext] || 'Text';
}

export function FileViewer({ sessionId, file, onClose }: FileViewerProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!file) return;
    
    const fileType = getFileType(file.name);
    
    // For images and PDFs, we don't need to load content
    if (fileType === 'image' || fileType === 'pdf') {
      setContent(null);
      return;
    }

    // Load text content
    const loadContent = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await readFile(sessionId, file.path);
        setContent(response.content);
      } catch (err) {
        setError('Failed to load file content');
      } finally {
        setLoading(false);
      }
    };

    loadContent();
  }, [file, sessionId]);

  if (!file) return null;

  const fileType = getFileType(file.name);
  const downloadUrl = `${API_BASE}/api/files/${sessionId}/download?path=${encodeURIComponent(file.path)}`;

  const handleCopy = async () => {
    if (content) {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    window.open(downloadUrl, '_blank');
  };

  const renderContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (error) {
      return (
        <Box sx={{ textAlign: 'center', p: 4 }}>
          <Typography color="error">{error}</Typography>
        </Box>
      );
    }

    // Image preview
    if (fileType === 'image') {
      return (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            bgcolor: '#1e1e2e',
            borderRadius: 2,
            p: 2,
            minHeight: 300,
          }}
        >
          <Box
            component="img"
            src={downloadUrl}
            alt={file.name}
            sx={{
              maxWidth: '100%',
              maxHeight: 500,
              objectFit: 'contain',
              borderRadius: 1,
            }}
          />
        </Box>
      );
    }

    // PDF preview
    if (fileType === 'pdf') {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            p: 4,
            bgcolor: '#1e1e2e',
            borderRadius: 2,
          }}
        >
          <PictureAsPdfIcon sx={{ fontSize: 80, color: '#f38ba8' }} />
          <Typography variant="h6">{file.name}</Typography>
          <Typography color="text.secondary" variant="body2">
            PDF files cannot be previewed inline
          </Typography>
          <Button
            variant="contained"
            startIcon={<OpenInNewIcon />}
            onClick={handleDownload}
          >
            Open PDF
          </Button>
        </Box>
      );
    }

    // Code/Text preview
    return (
      <Paper
        sx={{
          bgcolor: '#1e1e2e',
          borderRadius: 2,
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            maxHeight: 500,
            overflow: 'auto',
            '&::-webkit-scrollbar': { width: 8, height: 8 },
            '&::-webkit-scrollbar-thumb': {
              bgcolor: 'rgba(255,255,255,0.2)',
              borderRadius: 4,
            },
          }}
        >
          <Box sx={{ display: 'flex' }}>
            {/* Line Numbers */}
            <Box
              sx={{
                p: 2,
                pr: 1,
                bgcolor: '#11111b',
                borderRight: '1px solid',
                borderColor: 'divider',
                userSelect: 'none',
                position: 'sticky',
                left: 0,
              }}
            >
              {content?.split('\n').map((_, i) => (
                <Typography
                  key={i}
                  component="div"
                  sx={{
                    fontFamily: '"Fira Code", monospace',
                    fontSize: '0.8rem',
                    lineHeight: 1.6,
                    color: 'text.disabled',
                    textAlign: 'right',
                    minWidth: 30,
                  }}
                >
                  {i + 1}
                </Typography>
              ))}
            </Box>

            {/* Code Content */}
            <Box sx={{ p: 2, flex: 1, minWidth: 0 }}>
              <Typography
                component="pre"
                sx={{
                  fontFamily: '"Fira Code", monospace',
                  fontSize: '0.8rem',
                  lineHeight: 1.6,
                  color: '#cdd6f4',
                  whiteSpace: 'pre',
                  m: 0,
                }}
              >
                {content}
              </Typography>
            </Box>
          </Box>
        </Box>
      </Paper>
    );
  };

  return (
    <Dialog
      open={!!file}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: 'background.paper',
          backgroundImage: 'none',
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          {fileType === 'image' && <ImageIcon sx={{ color: '#89dceb' }} />}
          {fileType === 'pdf' && <PictureAsPdfIcon sx={{ color: '#f38ba8' }} />}
          {(fileType === 'code' || fileType === 'text') && <CodeIcon sx={{ color: '#a6e3a1' }} />}
          <Typography variant="h6" component="span" sx={{ fontFamily: 'monospace' }}>
            {file.name}
          </Typography>
          <Chip label={getLanguage(file.name)} size="small" variant="outlined" />
        </Stack>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {renderContent()}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ mr: 'auto' }}>
          {file.path}
        </Typography>
        {content && (
          <Button
            startIcon={copied ? <CheckIcon /> : <ContentCopyIcon />}
            onClick={handleCopy}
            color={copied ? 'success' : 'inherit'}
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        )}
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
        >
          Download
        </Button>
      </DialogActions>
    </Dialog>
  );
}
