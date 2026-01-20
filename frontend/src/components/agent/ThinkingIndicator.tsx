'use client';

import { Box, Paper, Typography, CircularProgress, Stack } from '@mui/material';
import PsychologyIcon from '@mui/icons-material/Psychology';

interface ThinkingIndicatorProps {
  thought: string | null;
}

export function ThinkingIndicator({ thought }: ThinkingIndicatorProps) {
  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: 'rgba(99, 102, 241, 0.1)',
        border: '1px solid',
        borderColor: 'primary.dark',
        animation: 'pulse 2s infinite',
        '@keyframes pulse': {
          '0%': { opacity: 1 },
          '50%': { opacity: 0.7 },
          '100%': { opacity: 1 },
        },
      }}
    >
      <Stack direction="row" spacing={2} alignItems="center">
        <CircularProgress size={20} color="primary" />
        <PsychologyIcon color="primary" />
        <Box>
          <Typography variant="subtitle2" color="primary">
            Agent is thinking...
          </Typography>
          {thought && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {thought.length > 200 ? `${thought.substring(0, 200)}...` : thought}
            </Typography>
          )}
        </Box>
      </Stack>
    </Paper>
  );
}
