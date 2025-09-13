// API Types
export const SessionStatus = {
  IDLE: 'idle',
  INDEXING: 'indexing',
  READY: 'ready',
  ERROR: 'error'
};

// App State Types
export const createInitialState = () => ({
  session: {
    id: null,
    status: SessionStatus.IDLE,
    repoUrl: '',
    progress: {},
  },
  queries: {
    history: [],
    currentQuery: '',
    isLoading: false,
  },
  ui: {
    showRepositoryInput: true,
    showQueryInterface: false,
    error: null,
  },
});

// Helper functions
export const createQueryHistory = (question, answer, sources, confidence) => ({
  id: Date.now().toString(),
  question,
  answer,
  sources,
  timestamp: new Date(),
  confidence,
});
