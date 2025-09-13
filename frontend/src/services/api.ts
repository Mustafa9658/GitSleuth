import axios from 'axios';
import {
  IndexRequest,
  IndexResponse,
  StatusResponse,
  QueryRequest,
  QueryResponse,
  ErrorResponse
} from '../types';

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
  static async indexRepository(repoUrl: string): Promise<IndexResponse> {
    const request: IndexRequest = { repo_url: repoUrl };
    const response = await api.post<IndexResponse>('/index', request);
    return response.data;
  }

  /**
   * Check indexing status
   */
  static async checkStatus(sessionId: string): Promise<StatusResponse> {
    const response = await api.get<StatusResponse>(`/status/${sessionId}`);
    return response.data;
  }

  /**
   * Query the codebase
   */
  static async queryCodebase(sessionId: string, question: string): Promise<QueryResponse> {
    const request: QueryRequest = { session_id: sessionId, question };
    const response = await api.post<QueryResponse>('/query', request);
    return response.data;
  }

  /**
   * Delete a session
   */
  static async deleteSession(sessionId: string): Promise<{ message: string }> {
    const response = await api.delete(`/session/${sessionId}`);
    return response.data;
  }

  /**
   * List all sessions
   */
  static async listSessions(): Promise<{
    total_sessions: number;
    status_breakdown: Record<string, number>;
    sessions: Array<{
      id: string;
      repo_url: string;
      status: string;
      created_at: string;
      total_files: number;
      total_chunks: number;
    }>;
  }> {
    const response = await api.get('/sessions');
    return response.data;
  }

  /**
   * Health check
   */
  static async healthCheck(): Promise<{ status: string; sessions: number }> {
    const response = await api.get('/health');
    return response.data;
  }
}

export default api;
