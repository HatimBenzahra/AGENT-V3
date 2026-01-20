'use client';

import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Stack,
  Chip,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import CodeIcon from '@mui/icons-material/Code';
import DescriptionIcon from '@mui/icons-material/Description';

interface FilePreviewProps {
  path: string;
  content: string;
  maxHeight?: number;
}

// Get language from file extension
function getLanguage(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  const langMap: Record<string, string> = {
    py: 'python',
    js: 'javascript',
    ts: 'typescript',
    jsx: 'javascript',
    tsx: 'typescript',
    json: 'json',
    md: 'markdown',
    html: 'html',
    css: 'css',
    sh: 'bash',
    bash: 'bash',
    yml: 'yaml',
    yaml: 'yaml',
    sql: 'sql',
    txt: 'text',
  };
  return langMap[ext] || 'text';
}

// Get icon for file type
function getFileIcon(path: string) {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  const codeExts = ['py', 'js', 'ts', 'jsx', 'tsx', 'json', 'html', 'css', 'sh', 'sql'];
  if (codeExts.includes(ext)) {
    return <CodeIcon fontSize="small" />;
  }
  return <DescriptionIcon fontSize="small" />;
}

export function FilePreview({ path, content, maxHeight = 400 }: FilePreviewProps) {
  const [copied, setCopied] = useState(false);
  const language = getLanguage(path);
  const fileName = path.split('/').pop() || path;
  const lineCount = content.split('\n').length;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Paper
      sx={{
        bgcolor: '#1e1e2e',
        borderRadius: 2,
        overflow: 'hidden',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      {/* File Header */}
      <Box
        sx={{
          px: 2,
          py: 1,
          bgcolor: '#181825',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center">
          {getFileIcon(path)}
          <Typography variant="body2" fontWeight={500}>
            {fileName}
          </Typography>
          <Chip
            label={language}
            size="small"
            variant="outlined"
            sx={{ height: 20, fontSize: '0.7rem' }}
          />
          <Typography variant="caption" color="text.secondary">
            {lineCount} lines
          </Typography>
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

      {/* File Content */}
      <Box
        sx={{
          maxHeight,
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
            }}
          >
            {content.split('\n').map((_, i) => (
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
          <Box sx={{ p: 2, flex: 1, overflow: 'auto' }}>
            <Typography
              component="pre"
              sx={{
                fontFamily: '"Fira Code", "Consolas", monospace',
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

      {/* File Path Footer */}
      <Box
        sx={{
          px: 2,
          py: 0.5,
          bgcolor: '#181825',
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
          {path}
        </Typography>
      </Box>
    </Paper>
  );
}
