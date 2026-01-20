'use client';

import { Paper, Typography, Stack, Chip, Box } from '@mui/material';
import BuildIcon from '@mui/icons-material/Build';
import SearchIcon from '@mui/icons-material/Search';
import HttpIcon from '@mui/icons-material/Http';
import CalculateIcon from '@mui/icons-material/Calculate';
import FolderIcon from '@mui/icons-material/Folder';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import TerminalIcon from '@mui/icons-material/Terminal';

interface ToolViewerProps {
  tool: string;
  params: Record<string, unknown>;
  result?: string;
}

const toolIcons: Record<string, React.ReactNode> = {
  web_search: <SearchIcon />,
  news_search: <SearchIcon />,
  http_request: <HttpIcon />,
  fetch_webpage: <HttpIcon />,
  calculator: <CalculateIcon />,
  list_directory: <FolderIcon />,
  read_file: <FolderIcon />,
  write_file: <SaveIcon />,
  delete_file: <DeleteIcon />,
  execute_command: <TerminalIcon />,
  save_output: <SaveIcon />,
};

const toolColors: Record<string, string> = {
  web_search: '#3b82f6',
  news_search: '#3b82f6',
  http_request: '#8b5cf6',
  fetch_webpage: '#8b5cf6',
  calculator: '#f59e0b',
  list_directory: '#10b981',
  read_file: '#10b981',
  write_file: '#10b981',
  delete_file: '#ef4444',
  execute_command: '#6366f1',
  save_output: '#06b6d4',
};

export function ToolViewer({ tool, params, result }: ToolViewerProps) {
  const icon = toolIcons[tool] || <BuildIcon />;
  const color = toolColors[tool] || '#6366f1';

  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: 'background.paper',
        border: '1px solid',
        borderColor: color,
        borderLeftWidth: 4,
      }}
    >
      <Stack direction="row" spacing={1} alignItems="center" mb={1}>
        <Box sx={{ color }}>{icon}</Box>
        <Typography variant="subtitle2" sx={{ color }}>
          {tool.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
        </Typography>
      </Stack>

      {/* Parameters */}
      {Object.keys(params).length > 0 && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Parameters:
          </Typography>
          <Box sx={{ pl: 2, mt: 0.5 }}>
            {Object.entries(params).map(([key, value]) => (
              <Typography
                key={key}
                variant="body2"
                sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
              >
                <Box component="span" sx={{ color: 'info.main' }}>
                  {key}
                </Box>
                :{' '}
                <Box component="span" sx={{ color: 'text.secondary' }}>
                  {typeof value === 'string'
                    ? value.length > 100
                      ? `${value.substring(0, 100)}...`
                      : value
                    : JSON.stringify(value)}
                </Box>
              </Typography>
            ))}
          </Box>
        </Box>
      )}

      {/* Result */}
      {result && (
        <Box
          sx={{
            mt: 1,
            p: 1,
            bgcolor: 'rgba(0,0,0,0.2)',
            borderRadius: 1,
            maxHeight: 200,
            overflow: 'auto',
          }}
        >
          <Typography
            variant="body2"
            sx={{
              fontFamily: 'monospace',
              fontSize: '0.75rem',
              whiteSpace: 'pre-wrap',
              color: 'text.secondary',
            }}
          >
            {result}
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
