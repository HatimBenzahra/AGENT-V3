'use client';

import { useState } from 'react';
import { Box, Drawer, useMediaQuery, useTheme, Fab, Tooltip, Badge } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { SessionList } from '@/components/session/SessionList';
import { FileBrowser, FileViewer } from '@/components/files';

const DRAWER_WIDTH = 280;
const FILES_DRAWER_WIDTH = 320;

interface FileInfo {
  name: string;
  path: string;
  size: number;
  is_directory: boolean;
}

export default function Home() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(!isMobile);
  const [filesDrawerOpen, setFilesDrawerOpen] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileInfo | null>(null);

  const handleSessionSelect = (sessionId: string | null) => {
    setCurrentSessionId(sessionId);
    if (isMobile) {
      setDrawerOpen(false);
    }
  };

  const handleNewSession = () => {
    setCurrentSessionId(null);
    setFilesDrawerOpen(false);
  };

  const handleFileSelect = (file: FileInfo) => {
    if (!file.is_directory) {
      setSelectedFile(file);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: 'background.default' }}>
      {/* Session Sidebar (Left) */}
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
          mr: filesDrawerOpen ? 0 : `-${FILES_DRAWER_WIDTH}px`,
          transition: theme.transitions.create(['margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
          ...(drawerOpen && {
            ml: 0,
          }),
          ...(filesDrawerOpen && {
            mr: 0,
          }),
        }}
      >
        <ChatContainer
          sessionId={currentSessionId}
          onMenuClick={() => setDrawerOpen(!drawerOpen)}
          onSessionCreated={(id) => setCurrentSessionId(id)}
        />

        {/* Files FAB Button */}
        {currentSessionId && !filesDrawerOpen && (
          <Tooltip title="View Files" placement="left">
            <Fab
              color="primary"
              size="medium"
              onClick={() => setFilesDrawerOpen(true)}
              sx={{
                position: 'fixed',
                bottom: 100,
                right: 24,
                zIndex: 1000,
              }}
            >
              <FolderIcon />
            </Fab>
          </Tooltip>
        )}
      </Box>

      {/* Files Sidebar (Right) */}
      <Drawer
        variant="persistent"
        anchor="right"
        open={filesDrawerOpen}
        sx={{
          width: FILES_DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: FILES_DRAWER_WIDTH,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
            borderLeft: '1px solid',
            borderColor: 'divider',
          },
        }}
      >
        <FileBrowser
          sessionId={currentSessionId}
          onFileSelect={handleFileSelect}
          onClose={() => setFilesDrawerOpen(false)}
        />
      </Drawer>

      {/* File Viewer Modal */}
      {currentSessionId && (
        <FileViewer
          sessionId={currentSessionId}
          file={selectedFile}
          onClose={() => setSelectedFile(null)}
        />
      )}
    </Box>
  );
}
