// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

// API Endpoints
export const API_ENDPOINTS = {
  // Admin
  admin: {
    users: '/admin/users',
    analytics: '/admin/analytics',
    records: '/admin/data/records',
    auditLogs: '/admin/audit/logs',
    hospitals: '/admin/hospitals',
    settings: '/admin/settings',
  },
  // Auth
  auth: {
    login: '/auth/login',
    signup: '/auth/signup',
    logout: '/auth/logout',
    refresh: '/auth/refresh',
  },
};

// Error Messages
export const ERROR_MESSAGES = {
  UNAUTHORIZED: 'You are not authorized to access this resource',
  FORBIDDEN: 'You do not have permission to perform this action',
  NOT_FOUND: 'The requested resource was not found',
  SERVER_ERROR: 'An error occurred on the server',
  NETWORK_ERROR: 'A network error occurred. Please check your connection.',
};
