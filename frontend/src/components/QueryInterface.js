import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  List,
  ListItem,
  Chip,
  Divider,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
} from '@mui/material';
import {
  Send,
  QuestionAnswer,
  Code,
  ExpandMore,
  Clear,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const QueryInterface = ({ sessionId, onQuery, queries, isLoading, error }) => {
  const [currentQuery, setCurrentQuery] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (currentQuery.trim() && !isLoading) {
      await onQuery(currentQuery);
      setCurrentQuery('');
    }
  };

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high': return 'success';
      case 'medium': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  const formatCodeBlock = (code, language) => {
    return (
      <SyntaxHighlighter
        language={language || 'text'}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          borderRadius: '4px',
        }}
      >
        {code}
      </SyntaxHighlighter>
    );
  };

  const renderSourceReference = (source, index) => (
    <Accordion key={index} sx={{ mb: 1 }}>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Box display="flex" alignItems="center" gap={1}>
          <Code fontSize="small" />
          <Typography variant="body2" fontWeight="medium">
            {source.file}
          </Typography>
          <Chip
            size="small"
            label={`Lines ${source.line_start}-${source.line_end}`}
            variant="outlined"
          />
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Box>
          {formatCodeBlock(source.snippet)}
        </Box>
      </AccordionDetails>
    </Accordion>
  );

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 2 }}>
      {/* Query Input */}
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Ask a Question
        </Typography>
        
        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth
            multiline
            rows={3}
            placeholder="Ask a question about the codebase... (e.g., 'How does authentication work?', 'Where is the database connection configured?')"
            value={currentQuery}
            onChange={(e) => setCurrentQuery(e.target.value)}
            disabled={isLoading}
            sx={{ mb: 2 }}
          />
          
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="body2" color="text.secondary">
              Session: {sessionId}
            </Typography>
            
            <Box>
              <Button
                type="submit"
                variant="contained"
                disabled={!currentQuery.trim() || isLoading}
                startIcon={isLoading ? <CircularProgress size={20} /> : <Send />}
              >
                {isLoading ? 'Thinking...' : 'Ask'}
              </Button>
            </Box>
          </Box>
        </form>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>

      {/* Query History */}
      {queries.length > 0 && (
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Query History ({queries.length})
            </Typography>
            <IconButton size="small" onClick={() => setCurrentQuery('')}>
              <Clear />
            </IconButton>
          </Box>

          <List>
            {queries.map((query, index) => (
              <React.Fragment key={query.id}>
                <ListItem alignItems="flex-start" sx={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  {/* Question */}
                  <Box sx={{ mb: 2 }}>
                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                      <QuestionAnswer fontSize="small" color="primary" />
                      <Typography variant="subtitle2" fontWeight="medium">
                        Question
                      </Typography>
                      <Chip
                        size="small"
                        label={query.timestamp.toLocaleTimeString()}
                        variant="outlined"
                      />
                      {query.confidence && (
                        <Chip
                          size="small"
                          label={`Confidence: ${query.confidence}`}
                          color={getConfidenceColor(query.confidence)}
                          variant="outlined"
                        />
                      )}
                    </Box>
                    <Typography variant="body1" sx={{ fontStyle: 'italic' }}>
                      {query.question}
                    </Typography>
                  </Box>

                  {/* Answer */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
                      Answer
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                      <ReactMarkdown
                        components={{
                          code: ({ className, children, ...props }) => {
                            const match = /language-(\w+)/.exec(className || '');
                            const isInline = !match;
                            return !isInline && match ? (
                              formatCodeBlock(String(children).replace(/\n$/, ''), match[1])
                            ) : (
                              <code className={className} {...props}>
                                {children}
                              </code>
                            );
                          },
                        }}
                      >
                        {query.answer}
                      </ReactMarkdown>
                    </Paper>
                  </Box>

                  {/* Sources */}
                  {query.sources.length > 0 && (
                    <Box>
                      <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
                        Sources ({query.sources.length})
                      </Typography>
                      <Box>
                        {query.sources.map((source, sourceIndex) =>
                          renderSourceReference(source, sourceIndex)
                        )}
                      </Box>
                    </Box>
                  )}
                </ListItem>
                
                {index < queries.length - 1 && <Divider sx={{ my: 2 }} />}
              </React.Fragment>
            ))}
          </List>
        </Box>
      )}

      {queries.length === 0 && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }}>
          <QuestionAnswer sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No questions yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Start by asking a question about the codebase above
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default QueryInterface;
