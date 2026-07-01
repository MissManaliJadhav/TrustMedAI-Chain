import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  message_type: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  status: string;
  conversation_stage: string;
  created_at: string;
  updated_at: string;
}

export interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  isComposing: boolean;
}

const initialState: ChatState = {
  sessions: [],
  currentSessionId: null,
  messages: [],
  loading: false,
  error: null,
  isComposing: false,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    // Session actions
    setSessions: (state, action: PayloadAction<ChatSession[]>) => {
      state.sessions = action.payload;
    },
    addSession: (state, action: PayloadAction<ChatSession>) => {
      state.sessions.unshift(action.payload);
      state.currentSessionId = action.payload.id;
      state.messages = [];
    },
    setCurrentSessionId: (state, action: PayloadAction<string>) => {
      state.currentSessionId = action.payload;
    },
    deleteSession: (state, action: PayloadAction<string>) => {
      state.sessions = state.sessions.filter(s => s.id !== action.payload);
      if (state.currentSessionId === action.payload) {
        state.currentSessionId = null;
        state.messages = [];
      }
    },

    // Message actions
    setMessages: (state, action: PayloadAction<ChatMessage[]>) => {
      state.messages = action.payload;
    },
    addUserMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    addAssistantMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messages.push(action.payload);
    },
    clearMessages: (state) => {
      state.messages = [];
    },

    // Loading states
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setIsComposing: (state, action: PayloadAction<boolean>) => {
      state.isComposing = action.payload;
    },
  },
});

export const {
  setSessions,
  addSession,
  setCurrentSessionId,
  deleteSession,
  setMessages,
  addUserMessage,
  addAssistantMessage,
  clearMessages,
  setLoading,
  setError,
  setIsComposing,
} = chatSlice.actions;

export default chatSlice.reducer;
