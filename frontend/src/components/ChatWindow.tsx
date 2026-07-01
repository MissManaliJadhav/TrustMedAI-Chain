import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  CircularProgress,
  Chip,
  Typography,
  Alert,
  Divider,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import { useAppDispatch, useAppSelector } from '../store';
import {
  addUserMessage,
  addAssistantMessage,
  setMessages,
  setLoading,
  setError,
  setCurrentSessionId,
  addSession,
  deleteSession as deleteSessionAction,
} from '../store/chatSlice';
import { chatAPI } from '../api/chatAPI';

interface ChatWindowProps {
  sessionId?: string;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ sessionId: initialSessionId }) => {
  const dispatch = useAppDispatch();
  const { currentSessionId, messages, loading, error, isComposing } = useAppSelector((state) => state.chat);

  const [inputValue, setInputValue] = useState('');
  const [assessment, setAssessment] = useState<any>(null);
  const [showAssessment, setShowAssessment] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const sessionId = initialSessionId || currentSessionId;

  useEffect(() => {
    if (initialSessionId) {
      dispatch(setCurrentSessionId(initialSessionId));
      loadMessages(initialSessionId);
    }
  }, [initialSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadMessages = async (id: string) => {
    try {
      dispatch(setLoading(true));
      const msgs = await chatAPI.getMessages(id);
      dispatch(setMessages(msgs));
      const session = await chatAPI.getSession(id);
      if (session.conversation_stage === 'completed') {
        const assessmentData = await chatAPI.getAssessment(id);
        setAssessment(assessmentData);
        setShowAssessment(true);
      } else {
        setAssessment(null);
        setShowAssessment(false);
      }
    } catch (err: any) {
      dispatch(setError(err.message));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const createNewSession = async () => {
    try {
      dispatch(setLoading(true));
      const session = await chatAPI.createSession('New Health Assessment');
      dispatch(addSession(session));
      setInputValue('');
      setAssessment(null);
      setShowAssessment(false);
    } catch (err: any) {
      dispatch(setError(err.message));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate message is not empty
    if (!inputValue.trim()) {
      dispatch(setError("Please enter a message"));
      setTimeout(() => dispatch(setError(null)), 3000);
      return;
    }

    // Validate session exists
    if (!sessionId) {
      dispatch(setError("No active chat session. Please create or select a session."));
      setTimeout(() => dispatch(setError(null)), 3000);
      return;
    }

    // Don't send while loading
    if (loading) return;

    const userMessage = inputValue;
    setInputValue('');

    try {
      dispatch(setLoading(true));

      const response = await chatAPI.sendMessage(sessionId, userMessage);

      dispatch(addUserMessage(response.user_message));
      dispatch(addAssistantMessage(response.assistant_message));

      // Load assessment if stage is completed
      if (response.assistant_message.content.includes('ASSESSMENT SUMMARY')) {
        const assessmentData = await chatAPI.getAssessment(sessionId);
        setAssessment(assessmentData);
        setShowAssessment(true);
      }
    } catch (err: any) {
      dispatch(setError(err.message || 'Failed to send message'));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleDeleteSession = async () => {
    if (!sessionId) return;

    if (window.confirm('Are you sure you want to delete this session?')) {
      try {
        await chatAPI.deleteSession(sessionId);
        dispatch(deleteSessionAction(sessionId));
      } catch (err: any) {
        dispatch(setError(err.message));
      }
    }
  };

  const handleExportAssessment = async () => {
    if (!sessionId) return;

    try {
      dispatch(setLoading(true));
      const result = await chatAPI.exportSession(sessionId);
      alert(`Assessment exported successfully! Diagnosis ID: ${result.diagnosis_id}`);
    } catch (err: any) {
      dispatch(setError(err.message || 'Failed to export assessment'));
    } finally {
      dispatch(setLoading(false));
    }
  };

  if (!sessionId) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Welcome to MedAI Assistant
        </Typography>
        <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
          Your AI-powered healthcare assistant. Start a new chat to get personalized health recommendations.
        </Typography>
        <button
          onClick={createNewSession}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#1976d2',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Start New Chat
        </button>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 2 }}>
      {error && <Alert severity="error">{error}</Alert>}

      {/* Messages Container */}
      <Paper
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          backgroundColor: '#f5f5f5',
        }}
      >
        {messages.length === 0 ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <Typography variant="body2" color="text.secondary">
              Start the conversation by introducing yourself...
            </Typography>
          </Box>
        ) : (
          <>
            {messages.map((msg) => (
              <Box
                key={msg.id}
                sx={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 1,
                }}
              >
                <Paper
                  sx={{
                    p: 1.5,
                    maxWidth: '70%',
                    backgroundColor: msg.role === 'user' ? '#1976d2' : '#e0e0e0',
                    color: msg.role === 'user' ? 'white' : 'black',
                    wordWrap: 'break-word',
                  }}
                >
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </Typography>
                </Paper>
              </Box>
            ))}
            {loading && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </Paper>

      {/* Assessment Display */}
      {showAssessment && assessment && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Health Assessment Summary</Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <IconButton
                  size="small"
                  onClick={handleExportAssessment}
                  title="Export Assessment"
                >
                  <DownloadIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  onClick={() => setShowAssessment(false)}
                  title="Close"
                >
                  ×
                </IconButton>
              </Box>
            </Box>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                  Risk Level
                </Typography>
                <Chip
                  label={assessment.risk_assessment?.overall_risk_score || 'MODERATE'}
                  color={
                    assessment.risk_assessment?.overall_risk_score === 'HIGH'
                      ? 'error'
                      : assessment.risk_assessment?.overall_risk_score === 'MODERATE'
                        ? 'warning'
                        : 'success'
                  }
                  size="small"
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                  Possible Conditions
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {assessment.possible_conditions?.slice(0, 3).map((condition: any, idx: number) => (
                    <Chip
                      key={idx}
                      label={`${condition.condition} (${Math.round(condition.probability)}%)`}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
              Recommended Actions
            </Typography>
            <ul style={{ margin: '0 0 1rem 0', paddingLeft: '20px' }}>
              {assessment.recommendations?.immediate_actions?.map((action: string, idx: number) => (
                <li key={idx}>{action}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Message Input */}
      <Box
        component="form"
        onSubmit={handleSendMessage}
        sx={{
          display: 'flex',
          gap: 1,
          pt: 2,
          borderTop: '1px solid #e0e0e0',
        }}
      >
        <TextField
          fullWidth
          placeholder="Type your message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={loading || !sessionId}
          size="small"
          multiline
          maxRows={3}
        />
        <IconButton
          type="submit"
          disabled={loading || !inputValue.trim() || !sessionId}
          color="primary"
        >
          <SendIcon />
        </IconButton>
        <IconButton
          onClick={handleDeleteSession}
          disabled={loading || !sessionId}
          color="error"
        >
          <DeleteIcon />
        </IconButton>
      </Box>
    </Box>
  );
};

export default ChatWindow;
