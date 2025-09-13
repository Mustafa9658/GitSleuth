import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Container,
  Alert,
  Snackbar,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  GitHub,
  Refresh,
  MoreVert,
  Home,
} from '@mui/icons-material';
import RepositoryInput from './components/RepositoryInput';
import IndexingStatus from './components/IndexingStatus';
import QueryInterface from './components/QueryInterface';
import { GitSleuthAPI } from './services/api';
import { usePolling } from './hooks/usePolling';
import { SessionStatus, createInitialState, createQueryHistory } from './types';

const App = () => {
  const [state, setState] = useState(createInitialState());

  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'info',
  });

  const [menuAnchor, setMenuAnchor] = useState(null);

  // Show snackbar notification
  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  // Handle repository indexing
  const handleIndexRepository = async (repoUrl) => {
    try {
      setState(prev => ({
        ...prev,
        ui: { ...prev.ui, error: null },
        queries: { ...prev.queries, isLoading: true },
      }));

      const response = await GitSleuthAPI.indexRepository(repoUrl);
      
      setState(prev => ({
        ...prev,
        session: {
          id: response.session_id,
          status: response.status,
          repoUrl,
          progress: {},
        },
        ui: {
          ...prev.ui,
          showRepositoryInput: false,
          showQueryInterface: false,
        },
        queries: { ...prev.queries, isLoading: false },
      }));

      showSnackbar('Repository indexing started!', 'success');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to start indexing';
      setState(prev => ({
        ...prev,
        ui: { ...prev.ui, error: errorMessage },
        queries: { ...prev.queries, isLoading: false },
      }));
      showSnackbar(errorMessage, 'error');
    }
  };

  // Check indexing status
  const checkStatus = useCallback(async () => {
    if (!state.session.id) return;

    try {
      const status = await GitSleuthAPI.checkStatus(state.session.id);
      
      setState(prev => ({
        ...prev,
        session: {
          ...prev.session,
          status: status.status,
          progress: status.progress || {},
        },
        ui: {
          ...prev.ui,
          showQueryInterface: status.status === SessionStatus.READY,
        },
      }));

      if (status.status === SessionStatus.READY) {
        showSnackbar('Repository indexing complete! You can now ask questions.', 'success');
      } else if (status.status === SessionStatus.ERROR) {
        showSnackbar(`Indexing failed: ${status.message}`, 'error');
      }
    } catch (error) {
      console.error('Status check failed:', error);
    }
  }, [state.session.id]);

  // Poll for status updates during indexing
  usePolling({
    enabled: state.session.status === SessionStatus.INDEXING,
    interval: 2000,
    onPoll: checkStatus,
  });

  // Handle query submission
  const handleQuery = async (question) => {
    if (!state.session.id) return;

    try {
      setState(prev => ({
        ...prev,
        queries: { ...prev.queries, isLoading: true },
        ui: { ...prev.ui, error: null },
      }));

      const response = await GitSleuthAPI.queryCodebase(state.session.id, question);
      
      const newQuery = createQueryHistory(
        question,
        response.answer,
        response.sources,
        response.confidence
      );

      setState(prev => ({
        ...prev,
        queries: {
          ...prev.queries,
          history: [newQuery, ...prev.queries.history],
          isLoading: false,
        },
      }));

      showSnackbar('Question answered!', 'success');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to process query';
      setState(prev => ({
        ...prev,
        queries: { ...prev.queries, isLoading: false },
        ui: { ...prev.ui, error: errorMessage },
      }));
      showSnackbar(errorMessage, 'error');
    }
  };

  // Reset application state
  const handleReset = () => {
    setState(createInitialState());
    setMenuAnchor(null);
    showSnackbar('Application reset', 'info');
  };

  // Handle menu actions
  const handleMenuOpen = (event) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleNewAnalysis = () => {
    handleReset();
    handleMenuClose();
  };

  // Check API health on startup
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await GitSleuthAPI.healthCheck();
      } catch (error) {
        showSnackbar('Backend API is not available. Please check if the server is running.', 'error');
      }
    };
    checkHealth();
  }, []);

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* App Bar */}
      <AppBar position="static">
        <Toolbar>
          <GitHub sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            GitSleuth
          </Typography>
          
          {state.session.id && (
            <Typography variant="body2" sx={{ mr: 2 }}>
              {state.session.repoUrl}
            </Typography>
          )}
          
          <IconButton
            color="inherit"
            onClick={handleMenuOpen}
            aria-label="menu"
          >
            <MoreVert />
          </IconButton>
          
          <Menu
            anchorEl={menuAnchor}
            open={Boolean(menuAnchor)}
            onClose={handleMenuClose}
          >
            <MenuItem onClick={handleNewAnalysis}>
              <Home sx={{ mr: 1 }} />
              New Analysis
            </MenuItem>
            <MenuItem onClick={handleReset}>
              <Refresh sx={{ mr: 1 }} />
              Reset
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ py: 4 }}>
        {state.ui.showRepositoryInput && (
          <RepositoryInput
            onIndex={handleIndexRepository}
            isLoading={state.queries.isLoading}
            error={state.ui.error || undefined}
          />
        )}

        {state.session.status === SessionStatus.INDEXING && (
          <IndexingStatus
            status={{
              status: state.session.status,
              message: 'Indexing in progress...',
              progress: state.session.progress,
            }}
            repoUrl={state.session.repoUrl}
          />
        )}

        {state.ui.showQueryInterface && state.session.id && (
          <QueryInterface
            sessionId={state.session.id}
            onQuery={handleQuery}
            queries={state.queries.history}
            isLoading={state.queries.isLoading}
            error={state.ui.error || undefined}
          />
        )}
      </Container>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default App;
