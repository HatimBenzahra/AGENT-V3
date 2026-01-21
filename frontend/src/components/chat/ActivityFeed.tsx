'use client';

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  CircularProgress,
  Chip,
} from '@mui/material';
import TerminalIcon from '@mui/icons-material/Terminal';
import FolderIcon from '@mui/icons-material/Folder';
import SearchIcon from '@mui/icons-material/Search';
import DescriptionIcon from '@mui/icons-material/Description';
import CalculateIcon from '@mui/icons-material/Calculate';
import BuildIcon from '@mui/icons-material/Build';
import ErrorIcon from '@mui/icons-material/Error';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { Activity, AgentStatus, ActivityType } from '@/lib/types';

interface ActivityFeedProps {
  activities: Activity[];
  status: AgentStatus;
}

const activityConfig: Record<ActivityType, { icon: React.ElementType; label: string; color: string }> = {
  terminal: { icon: TerminalIcon, label: 'Running command', color: '#4ec9b0' },
  file: { icon: FolderIcon, label: 'File operation', color: '#dcdcaa' },
  search: { icon: SearchIcon, label: 'Searching', color: '#569cd6' },
  document: { icon: DescriptionIcon, label: 'Creating document', color: '#ce9178' },
  compute: { icon: CalculateIcon, label: 'Computing', color: '#b5cea8' },
  tool: { icon: BuildIcon, label: 'Using tool', color: '#9cdcfe' },
  error: { icon: ErrorIcon, label: 'Error', color: '#f14c4c' },
};

export function ActivityFeed({ activities, status }: ActivityFeedProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const statusLabels: Record<AgentStatus, string> = {
    idle: '',
    planning: 'Planning...',
    thinking: 'Thinking...',
    working: 'Working...',
  };

  return (
    <Paper
      elevation={0}
      sx={{
        mt: 2,
        p: 2,
        bgcolor: 'grey.900',
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <CircularProgress size={16} thickness={5} sx={{ color: 'primary.main' }} />
        <Typography variant="subtitle2" sx={{ color: 'grey.300' }}>
          {statusLabels[status] || 'Working...'}
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {activities.map((activity) => (
          <ActivityItem
            key={activity.id}
            activity={activity}
            expanded={expandedId === activity.id}
            onToggle={() => setExpandedId(expandedId === activity.id ? null : activity.id)}
          />
        ))}
      </Box>
    </Paper>
  );
}

function ActivityItem({
  activity,
  expanded,
  onToggle,
}: {
  activity: Activity;
  expanded: boolean;
  onToggle: () => void;
}) {
  const config = activityConfig[activity.type] || activityConfig.tool;
  const Icon = config.icon;
  const isRunning = activity.status === 'running';
  const isFailed = activity.status === 'failed';

  const getToolLabel = (tool: string) => {
    const labels: Record<string, string> = {
      terminal: 'Terminal',
      execute_command: 'Terminal',
      write_file: 'Writing file',
      read_file: 'Reading file',
      list_directory: 'Listing directory',
      delete_file: 'Deleting file',
      web_search: 'Web search',
      news_search: 'News search',
      fetch_webpage: 'Fetching page',
      http_request: 'HTTP request',
      create_pdf: 'Creating PDF',
      calculator: 'Calculating',
    };
    return labels[tool] || tool;
  };

  const getDescription = () => {
    if (activity.tool === 'terminal' || activity.tool === 'execute_command') {
      const cmd = activity.params?.command as string;
      return cmd ? `$ ${cmd.length > 50 ? cmd.slice(0, 50) + '...' : cmd}` : '';
    }
    if (activity.tool === 'write_file' || activity.tool === 'read_file') {
      const path = activity.params?.file_path as string;
      return path || '';
    }
    if (activity.tool === 'web_search' || activity.tool === 'news_search') {
      const query = activity.params?.query as string;
      return query ? `"${query}"` : '';
    }
    return '';
  };

  return (
    <Box
      sx={{
        bgcolor: 'grey.800',
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          p: 1,
          cursor: activity.result ? 'pointer' : 'default',
        }}
        onClick={activity.result ? onToggle : undefined}
      >
        {isRunning ? (
          <CircularProgress size={16} thickness={5} sx={{ color: config.color }} />
        ) : isFailed ? (
          <ErrorIcon sx={{ fontSize: 16, color: 'error.main' }} />
        ) : (
          <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />
        )}

        <Icon sx={{ fontSize: 16, color: config.color }} />

        <Typography
          variant="body2"
          sx={{ color: 'grey.300', flexGrow: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}
        >
          {getToolLabel(activity.tool)}
        </Typography>

        <Typography
          variant="caption"
          sx={{
            color: 'grey.500',
            maxWidth: 200,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontFamily: 'monospace',
          }}
        >
          {getDescription()}
        </Typography>

        {activity.result && (
          <IconButton size="small" sx={{ color: 'grey.500', p: 0.5 }}>
            {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
        )}
      </Box>

      <Collapse in={expanded}>
        <Box
          sx={{
            p: 1,
            pt: 0,
            maxHeight: 200,
            overflow: 'auto',
          }}
        >
          <Typography
            component="pre"
            sx={{
              m: 0,
              p: 1,
              bgcolor: 'grey.900',
              borderRadius: 0.5,
              fontSize: '0.75rem',
              fontFamily: 'monospace',
              color: isFailed ? 'error.light' : 'grey.400',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            {activity.error || activity.result}
          </Typography>
        </Box>
      </Collapse>
    </Box>
  );
}
