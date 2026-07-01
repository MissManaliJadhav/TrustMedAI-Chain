import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('trustmedai_access');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
