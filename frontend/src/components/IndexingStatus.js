import React from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Paper,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  Storage,
  Code,
  Speed,
  CheckCircle,
} from '@mui/icons-material';

const IndexingStatus = ({ status, repoUrl }) => {
  const getProgressValue = () => {
    if (!status.progress) return 0;
    
    const { processed_files = 0, total_files = 0 } = status.progress;
    if (total_files === 0) return 0;
    
    return Math.round((processed_files / total_files) * 100);
  };

  const getStepIcon = (step) => {
    switch (step) {
      case 'scanning_files':
        return <Storage />;
      case 'processing_files':
        return <Code />;
      case 'generating_embeddings':
        return <Speed />;
      case 'storing_vectors':
        return <Storage />;
      case 'complete':
        return <CheckCircle />;
      default:
        return <Code />;
    }
  };

  const getStepDescription = (step) => {
    switch (step) {
      case 'scanning_files':
        return 'Scanning repository files...';
      case 'processing_files':
        return 'Processing and chunking files...';
      case 'generating_embeddings':
        return 'Generating AI embeddings...';
      case 'storing_vectors':
        return 'Storing in vector database...';
      case 'complete':
        return 'Indexing complete!';
      default:
        return 'Processing...';
    }
  };

  const isError = status.status === 'error';
  const isComplete = status.status === 'ready';

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Box textAlign="center" mb={3}>
        <Typography variant="h5" component="h2" gutterBottom>
          {isError ? 'Indexing Failed' : isComplete ? 'Indexing Complete!' : 'Indexing Repository'}
        </Typography>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {repoUrl}
        </Typography>

        <Chip
          label={status.status.toUpperCase()}
          color={isError ? 'error' : isComplete ? 'success' : 'primary'}
          variant="outlined"
        />
      </Box>

      {isError ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          {status.message}
        </Alert>
      ) : (
        <>
          <Box mb={3}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="text.secondary">
                Progress
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {getProgressValue()}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={getProgressValue()}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>

          {status.progress && (
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Current Step
              </Typography>
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    {getStepIcon(status.progress.step || '')}
                  </ListItemIcon>
                  <ListItemText
                    primary={getStepDescription(status.progress.step || '')}
                    secondary={status.message}
                  />
                </ListItem>
              </List>
            </Box>
          )}

          {status.progress && (status.progress.total_files || status.progress.total_chunks) && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Statistics
              </Typography>
              <Box display="flex" gap={2} flexWrap="wrap">
                {status.progress.total_files && (
                  <Chip
                    icon={<Code />}
                    label={`${status.progress.processed_files || 0}/${status.progress.total_files} files`}
                    variant="outlined"
                  />
                )}
                {status.progress.total_chunks && (
                  <Chip
                    icon={<Storage />}
                    label={`${status.progress.processed_chunks || 0}/${status.progress.total_chunks} chunks`}
                    variant="outlined"
                  />
                )}
              </Box>
            </Box>
          )}
        </>
      )}
    </Paper>
  );
};

export default IndexingStatus;
