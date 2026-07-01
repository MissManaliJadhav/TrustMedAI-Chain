import axios from 'axios';
import { ChatSession, ChatMessage } from '../store/chatSlice';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('trustmedai_access');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const chatAPI = {
  // Session endpoints
  createSession: async (title: string = 'New Chat'): Promise<ChatSession> => {
    const response = await api.post('/chat/sessions', { title });
    return response.data;
  },

  listSessions: async (): Promise<ChatSession[]> => {
    const response = await api.get('/chat/sessions');
    return response.data;
  },

  getSession: async (sessionId: string): Promise<ChatSession> => {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  deleteSession: async (sessionId: string): Promise<{ status: string; message: string }> => {
    const response = await api.delete(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  // Message endpoints
  sendMessage: async (
    sessionId: string,
    content: string,
    messageType: string = 'text'
  ): Promise<{ user_message: ChatMessage; assistant_message: ChatMessage }> => {
    const response = await api.post('/chat/messages', {
      session_id: sessionId,
      content,
      message_type: messageType,
    });
    return response.data;
  },

  getMessages: async (sessionId: string): Promise<ChatMessage[]> => {
    const response = await api.get(`/chat/sessions/${sessionId}/messages`);
    return response.data;
  },

  // Assessment endpoints
  getAssessment: async (sessionId: string) => {
    const response = await api.get(`/chat/sessions/${sessionId}/assessment`);
    return response.data;
  },

  exportSession: async (sessionId: string, diseaseKey: string = 'general_health_assessment') => {
    const response = await api.post(`/chat/sessions/${sessionId}/export`, {
      disease_key: diseaseKey,
    });
    return response.data;
  },
};

export default api;
