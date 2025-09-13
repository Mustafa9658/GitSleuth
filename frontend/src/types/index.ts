// API Types
export interface IndexRequest {
  repo_url: string;
}

export interface IndexResponse {
  message: string;
  session_id: string;
  status: SessionStatus;
}

export interface StatusResponse {
  status: SessionStatus;
  message: string;
  progress?: {
    step?: string;
    processed_files?: number;
    total_files?: number;
    processed_chunks?: number;
    total_chunks?: number;
  };
}

export interface QueryRequest {
  session_id: string;
  question: string;
}

export interface SourceReference {
  file: string;
  snippet: string;
  line_start: number;
  line_end: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceReference[];
  confidence?: string;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
}

export enum SessionStatus {
  IDLE = 'idle',
  INDEXING = 'indexing',
  READY = 'ready',
  ERROR = 'error'
}

// App State Types
export interface AppState {
  session: {
    id: string | null;
    status: SessionStatus;
    repoUrl: string;
    progress: StatusResponse['progress'];
  };
  queries: {
    history: QueryHistory[];
    currentQuery: string;
    isLoading: boolean;
  };
  ui: {
    showRepositoryInput: boolean;
    showQueryInterface: boolean;
    error: string | null;
  };
}

export interface QueryHistory {
  id: string;
  question: string;
  answer: string;
  sources: SourceReference[];
  timestamp: Date;
  confidence?: string;
}
