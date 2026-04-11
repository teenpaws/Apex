import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT from localStorage on every request
apiClient.interceptors.request.use((config) => {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('apex_token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Global error interceptor — surface 401 for auth redirect
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('apex_token');
        window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  }
);

// ── API helpers ────────────────────────────────────────────────────────────────

export const signalsApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get('/signals', { params }),
  get: (id: string) => apiClient.get(`/signals/${id}`),
  ingest: () => apiClient.post('/signals/ingest'),
};

export const opportunitiesApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get('/opportunities', { params }),
  get: (id: string) => apiClient.get(`/opportunities/${id}`),
  refresh: (id: string) => apiClient.post(`/opportunities/${id}/refresh`),
};

export const actionsApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get('/actions', { params }),
  update: (id: string, data: Record<string, unknown>) =>
    apiClient.put(`/actions/${id}`, data),
  draftEmail: (id: string) => apiClient.post(`/actions/${id}/draft-email`),
};

export const outreachApi = {
  list: (params?: Record<string, string | number>) =>
    apiClient.get('/outreach', { params }),
  draft: (data: Record<string, unknown>) =>
    apiClient.post('/outreach/draft', data),
  send: (id: string) => apiClient.post(`/outreach/${id}/send`),
  connectGmail: () => apiClient.post('/outreach/oauth/connect'),
};

export const profileApi = {
  get: () => apiClient.get('/profile'),
  update: (data: Record<string, unknown>) => apiClient.put('/profile', data),
  analyze: () => apiClient.post('/profile/analyze'),
};

export const companiesApi = {
  get: (id: string) => apiClient.get(`/companies/${id}`),
};

export const contactsApi = {
  list: () => apiClient.get('/contacts'),
  search: (data: Record<string, unknown>) =>
    apiClient.post('/contacts/search', data),
  get: (id: string) => apiClient.get(`/contacts/${id}`),
};

export const agentsApi = {
  runStatus: (runId: string) =>
    apiClient.get(`/agents/run-status/${runId}`),
  runs: () => apiClient.get('/agents/runs'),
};

export const analyticsApi = {
  dashboard: () => apiClient.get('/analytics/dashboard'),
  costs: (params?: Record<string, string>) =>
    apiClient.get('/analytics/costs', { params }),
};
