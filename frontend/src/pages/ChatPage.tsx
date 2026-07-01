import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Drawer,
  IconButton,
  Divider,
  CircularProgress,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AddIcon from '@mui/icons-material/Add';
import { useAppDispatch, useAppSelector } from '../store';
import {
  setSessions,
  setCurrentSessionId,
  addSession,
} from '../store/chatSlice';
import ChatWindow from '../components/ChatWindow';
import { chatAPI } from '../api/chatAPI';

const ChatPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const { sessions, currentSessionId, loading } = useAppSelector((state) => state.chat);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, [dispatch]);

  const loadSessions = async () => {
    try {
      setSessionsLoading(true);
      const data = await chatAPI.listSessions();
      dispatch(setSessions(data));
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const handleCreateSession = async () => {
    try {
      const session = await chatAPI.createSession('New Health Assessment');
      dispatch(addSession(session));
      setMobileOpen(false);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    dispatch(setCurrentSessionId(sessionId));
    setMobileOpen(false);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Grid container spacing={3} sx={{ height: 'calc(100vh - 100px)' }}>
        {/* Sidebar */}
        <Grid
          item
          xs={12}
          sm={3}
          sx={{
            display: { xs: 'none', sm: 'block' },
            height: '100%',
          }}
        >
          <Paper
            sx={{
              p: 2,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'auto',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">Chat Sessions</Typography>
              <Button
                startIcon={<AddIcon />}
                size="small"
                onClick={handleCreateSession}
                variant="contained"
              >
                New
              </Button>
            </Box>

            <Divider sx={{ mb: 2 }} />

            {sessionsLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                <CircularProgress size={24} />
              </Box>
            ) : sessions.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                No chat sessions yet. Create one to start!
              </Typography>
            ) : (
              <List sx={{ flex: 1, overflow: 'auto' }}>
                {sessions.map((session) => (
                  <ListItem key={session.id} disablePadding sx={{ mb: 1 }}>
                    <ListItemButton
                      selected={currentSessionId === session.id}
                      onClick={() => handleSelectSession(session.id)}
                      sx={{
                        borderRadius: 1,
                        backgroundColor: currentSessionId === session.id ? '#e3f2fd' : 'transparent',
                      }}
                    >
                      <ListItemText
                        primary={session.title}
                        secondary={new Date(session.created_at).toLocaleDateString()}
                        primaryTypographyProps={{ noWrap: true, variant: 'body2' }}
                        secondaryTypographyProps={{ variant: 'caption' }}
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Main Chat Area */}
        <Grid
          item
          xs={12}
          sm={9}
          sx={{
            height: '100%',
          }}
        >
          {/* Mobile Header */}
          <Box sx={{ display: { xs: 'flex', sm: 'none' }, alignItems: 'center', mb: 2 }}>
            <IconButton onClick={() => setMobileOpen(true)}>
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" sx={{ flex: 1, ml: 2 }}>
              MedAI Assistant
            </Typography>
            <Button
              startIcon={<AddIcon />}
              size="small"
              onClick={handleCreateSession}
              variant="contained"
            >
              New Chat
            </Button>
          </Box>

          {/* Mobile Drawer */}
          <Drawer
            anchor="left"
            open={mobileOpen}
            onClose={() => setMobileOpen(false)}
            sx={{ display: { xs: 'block', sm: 'none' } }}
          >
            <Box sx={{ width: 250, p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">Chat Sessions</Typography>
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  onClick={handleCreateSession}
                  variant="contained"
                >
                  New
                </Button>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {sessionsLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : sessions.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                  No chat sessions yet
                </Typography>
              ) : (
                <List>
                  {sessions.map((session) => (
                    <ListItem key={session.id} disablePadding sx={{ mb: 1 }}>
                      <ListItemButton
                        onClick={() => {
                          handleSelectSession(session.id);
                          setMobileOpen(false);
                        }}
                      >
                        <ListItemText
                          primary={session.title}
                          secondary={new Date(session.created_at).toLocaleDateString()}
                        />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              )}
            </Box>
          </Drawer>

          {/* Chat Window */}
          <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
            {currentSessionId ? (
              <ChatWindow sessionId={currentSessionId} />
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h5" sx={{ mb: 2 }}>
                    Welcome to MedAI Assistant
                  </Typography>
                  <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
                    Your AI-powered healthcare companion. Start a new chat to get personalized health guidance.
                  </Typography>
                  <Button
                    variant="contained"
                    size="large"
                    startIcon={<AddIcon />}
                    onClick={handleCreateSession}
                  >
                    Start New Chat
                  </Button>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default ChatPage;
