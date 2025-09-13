import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Response error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export class GitSleuthAPI {
  /**
   * Start indexing a repository
   */
  static async indexRepository(repoUrl) {
    const request = { repo_url: repoUrl };
    const response = await api.post('/index', request);
    return response.data;
  }

  /**
   * Check indexing status
   */
  static async checkStatus(sessionId) {
    const response = await api.get(`/status/${sessionId}`);
    return response.data;
  }

  /**
   * Query the codebase
   */
  static async queryCodebase(sessionId, question) {
    const request = { session_id: sessionId, question };
    const response = await api.post('/query', request);
    return response.data;
  }

  /**
   * Delete a session
   */
  static async deleteSession(sessionId) {
    const response = await api.delete(`/session/${sessionId}`);
    return response.data;
  }

  /**
   * List all sessions
   */
  static async listSessions() {
    const response = await api.get('/sessions');
    return response.data;
  }

  /**
   * Health check
   */
  static async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  }
}

export default api;
