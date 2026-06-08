import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('trustmedai_access');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
