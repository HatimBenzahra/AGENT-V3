'use client';

import { useState } from 'react';
import { Box, Drawer, useMediaQuery, useTheme } from '@mui/material';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { SessionList } from '@/components/session/SessionList';

const DRAWER_WIDTH = 280;

export default function Home() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const handleSessionSelect = (sessionId: string | null) => {
    setCurrentSessionId(sessionId);
    if (isMobile) {
      setDrawerOpen(false);
    }
  };

  const handleNewSession = () => {
    setCurrentSessionId(null);
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: 'background.default' }}>
      {/* Session Sidebar */}
      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
            borderRight: '1px solid',
            borderColor: 'divider',
          },
        }}
      >
        <SessionList
          currentSessionId={currentSessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
        />
      </Drawer>

      {/* Main Chat Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          height: '100vh',
          overflow: 'hidden',
          ml: !isMobile && drawerOpen ? 0 : `-${DRAWER_WIDTH}px`,
          transition: theme.transitions.create('margin', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          ...(drawerOpen && {
            ml: 0,
            transition: theme.transitions.create('margin', {
              easing: theme.transitions.easing.easeOut,
              duration: theme.transitions.duration.enteringScreen,
            }),
          }),
        }}
      >
        <ChatContainer
          sessionId={currentSessionId}
          onMenuClick={() => setDrawerOpen(!drawerOpen)}
          onSessionCreated={(id) => setCurrentSessionId(id)}
        />
      </Box>
    </Box>
  );
}
