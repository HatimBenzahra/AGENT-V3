'use client';

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
  Chip,
  IconButton,
  Collapse,
  Tooltip,
  Fade,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import StopIcon from '@mui/icons-material/Stop';
import RefreshIcon from '@mui/icons-material/Refresh';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';

interface SuggestionPanelProps {
  isProcessing: boolean;
  onSuggest: (suggestion: string) => void;
  onInterrupt: () => void;
  currentThought?: string | null;
}

// Quick suggestion templates
const QUICK_SUGGESTIONS = [
  { label: 'Use different approach', value: 'Try a different approach to solve this' },
  { label: 'Add more details', value: 'Please add more details and explanation' },
  { label: 'Focus on...', value: 'Focus on the main objective first' },
  { label: 'Skip this step', value: 'Skip this step and move to the next one' },
  { label: 'Save progress', value: 'Save the current progress before continuing' },
];

export function SuggestionPanel({
  isProcessing,
  onSuggest,
  onInterrupt,
  currentThought,
}: SuggestionPanelProps) {
  const [suggestion, setSuggestion] = useState('');
  const [expanded, setExpanded] = useState(true);
  const [sentSuggestions, setSentSuggestions] = useState<string[]>([]);

  const handleSend = () => {
    if (suggestion.trim()) {
      onSuggest(suggestion.trim());
      setSentSuggestions((prev) => [...prev, suggestion.trim()]);
      setSuggestion('');
    }
  };

  const handleQuickSuggestion = (value: string) => {
    onSuggest(value);
    setSentSuggestions((prev) => [...prev, value]);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isProcessing) {
    return null;
  }

  return (
    <Fade in={isProcessing}>
      <Paper
        elevation={3}
        sx={{
          position: 'absolute',
          bottom: 80,
          right: 16,
          left: 16,
          maxWidth: 500,
          mx: 'auto',
          borderRadius: 2,
          overflow: 'hidden',
          bgcolor: 'background.paper',
          border: '1px solid',
          borderColor: 'primary.main',
          zIndex: 10,
        }}
      >
        {/* Header */}
        <Box
          sx={{
            px: 2,
            py: 1,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <TipsAndUpdatesIcon fontSize="small" />
            <Typography variant="subtitle2" fontWeight={600}>
              Guide the Agent
            </Typography>
          </Stack>
          <Stack direction="row" spacing={0.5}>
            <Tooltip title="Stop and restart">
              <IconButton size="small" onClick={onInterrupt} sx={{ color: 'inherit' }}>
                <StopIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <IconButton
              size="small"
              onClick={() => setExpanded(!expanded)}
              sx={{ color: 'inherit' }}
            >
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Stack>
        </Box>

        <Collapse in={expanded}>
          <Box sx={{ p: 2 }}>
            {/* Current thought indicator */}
            {currentThought && (
              <Box
                sx={{
                  mb: 2,
                  p: 1.5,
                  bgcolor: 'action.hover',
                  borderRadius: 1,
                  borderLeft: '3px solid',
                  borderColor: 'info.main',
                }}
              >
                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                  Agent is thinking:
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                  {currentThought.length > 150
                    ? `${currentThought.substring(0, 150)}...`
                    : currentThought}
                </Typography>
              </Box>
            )}

            {/* Quick suggestions */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                Quick suggestions:
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                {QUICK_SUGGESTIONS.map((qs) => (
                  <Chip
                    key={qs.label}
                    label={qs.label}
                    size="small"
                    variant="outlined"
                    onClick={() => handleQuickSuggestion(qs.value)}
                    sx={{
                      mb: 0.5,
                      cursor: 'pointer',
                      '&:hover': {
                        bgcolor: 'primary.main',
                        color: 'primary.contrastText',
                      },
                    }}
                  />
                ))}
              </Stack>
            </Box>

            {/* Custom suggestion input */}
            <Stack direction="row" spacing={1}>
              <TextField
                fullWidth
                size="small"
                placeholder="Type your suggestion..."
                value={suggestion}
                onChange={(e) => setSuggestion(e.target.value)}
                onKeyPress={handleKeyPress}
                multiline
                maxRows={2}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: 'background.default',
                  },
                }}
              />
              <Button
                variant="contained"
                size="small"
                onClick={handleSend}
                disabled={!suggestion.trim()}
                sx={{ minWidth: 'auto', px: 2 }}
              >
                <SendIcon fontSize="small" />
              </Button>
            </Stack>

            {/* Sent suggestions history */}
            {sentSuggestions.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Sent suggestions:
                </Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                  {sentSuggestions.slice(-3).map((s, i) => (
                    <Chip
                      key={i}
                      label={s.length > 30 ? `${s.substring(0, 30)}...` : s}
                      size="small"
                      color="success"
                      variant="outlined"
                      sx={{ mb: 0.5 }}
                    />
                  ))}
                </Stack>
              </Box>
            )}
          </Box>
        </Collapse>
      </Paper>
    </Fade>
  );
}
