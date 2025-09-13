import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  CircularProgress,
  InputAdornment,
} from '@mui/material';
import { GitHub, Link as LinkIcon } from '@mui/icons-material';

const RepositoryInput = ({ onIndex, isLoading, error }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [validationError, setValidationError] = useState('');

  const validateUrl = (url) => {
    const githubPattern = /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;
    return githubPattern.test(url);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!repoUrl.trim()) {
      setValidationError('Please enter a repository URL');
      return;
    }

    if (!validateUrl(repoUrl)) {
      setValidationError('Please enter a valid GitHub repository URL (e.g., https://github.com/user/repo)');
      return;
    }

    setValidationError('');
    onIndex(repoUrl);
  };

  const handleUrlChange = (e) => {
    setRepoUrl(e.target.value);
    if (validationError) {
      setValidationError('');
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Box textAlign="center" mb={3}>
        <GitHub sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          GitSleuth
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          AI-powered GitHub repository analysis tool
        </Typography>
      </Box>

      <form onSubmit={handleSubmit}>
        <TextField
          fullWidth
          label="GitHub Repository URL"
          placeholder="https://github.com/username/repository"
          value={repoUrl}
          onChange={handleUrlChange}
          disabled={isLoading}
          error={!!validationError || !!error}
          helperText={validationError || error}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <LinkIcon color="action" />
              </InputAdornment>
            ),
          }}
          sx={{ mb: 3 }}
        />

        <Button
          type="submit"
          variant="contained"
          size="large"
          fullWidth
          disabled={isLoading || !repoUrl.trim()}
          startIcon={isLoading ? <CircularProgress size={20} /> : <GitHub />}
        >
          {isLoading ? 'Starting Analysis...' : 'Analyze Repository'}
        </Button>
      </form>

      <Box mt={3}>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          Enter a public GitHub repository URL to start analyzing its codebase with AI
        </Typography>
      </Box>
    </Paper>
  );
};

export default RepositoryInput;
