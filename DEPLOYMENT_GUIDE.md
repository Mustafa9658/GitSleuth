# GitSleuth Deployment Guide

This guide explains how to properly configure and deploy GitSleuth with environment variables for security and flexibility.

## Environment Configuration

### Backend Environment Variables

1. **Copy the example environment file:**
   ```bash
   cd backend
   cp env.example .env
   ```

2. **Edit the `.env` file with your actual values:**
   ```env
   # GitSleuth Backend Environment Configuration

   # OpenAI API Configuration
   OPENAI_API_KEY=your_actual_openai_api_key_here

   # Server Configuration
   HOST=0.0.0.0
   PORT=8000

   # Vector Store Configuration
   CHROMA_PERSIST_DIRECTORY=./chroma_db

   # File Processing Configuration
   MAX_FILE_SIZE=1000000
   MAX_FILES_PER_REPO=1000

   # Chunking Configuration
   CHUNK_SIZE=1000
   CHUNK_OVERLAP=200

   # RAG Configuration
   MAX_CONTEXT_CHUNKS=12
   SIMILARITY_THRESHOLD=0.15

   # Environment Configuration
   ENVIRONMENT=production
   DEBUG=false
   ```

### Frontend Environment Variables

1. **Copy the example environment file:**
   ```bash
   cd frontend
   cp env.example .env
   ```

2. **Edit the `.env` file with your actual values:**
   ```env
   # GitSleuth Frontend Environment Configuration

   # Backend API Configuration
   REACT_APP_API_URL=http://your-backend-domain.com:8000

   # Environment Configuration
   REACT_APP_ENVIRONMENT=production
   REACT_APP_DEBUG=false

   # Optional: Custom branding
   REACT_APP_APP_NAME=GitSleuth
   REACT_APP_APP_VERSION=1.0.0
   ```

## Deployment Configurations

### Development Environment

**Backend (.env):**
```env
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

**Frontend (.env):**
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
REACT_APP_DEBUG=true
```

### Production Environment

**Backend (.env):**
```env
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

**Frontend (.env):**
```env
REACT_APP_API_URL=https://your-backend-domain.com
REACT_APP_ENVIRONMENT=production
REACT_APP_DEBUG=false
```

## Security Notes

1. **Never commit `.env` files to version control**
2. **Use strong, unique API keys**
3. **Set `DEBUG=false` in production**
4. **Use HTTPS in production**
5. **Consider using environment variable management services for production**

## Docker Deployment

### Backend-Only Deployment (Recommended for Netlify Frontend)

If you're deploying the frontend separately (e.g., on Netlify), use the backend-only deployment:

```bash
# Development deployment
docker-compose -f docker-compose.backend.yml up -d

# Production deployment with nginx
docker-compose -f docker-compose.prod.backend.yml up -d

# Or use the deployment script
./deploy_backend.sh
```

**Backend-only deployment includes:**
- FastAPI backend service
- Nginx reverse proxy (optional)
- Persistent data volumes
- Health checks and monitoring
- CORS configuration for external frontend

### Backend Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Environment variables will be passed at runtime
CMD ["python", "main.py"]
```

### Frontend Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build the app
RUN npm run build

# Serve the built app
FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENVIRONMENT=production
      - DEBUG=false
    volumes:
      - ./backend/chroma_db:/app/chroma_db

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://backend:8000
      - REACT_APP_ENVIRONMENT=production
    depends_on:
      - backend
```

## Environment Variable Reference

### Backend Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM | - | Yes |
| `HOST` | Server host address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `CHROMA_PERSIST_DIRECTORY` | Vector database directory | `./chroma_db` | No |
| `MAX_FILE_SIZE` | Maximum file size in bytes | `1000000` | No |
| `MAX_FILES_PER_REPO` | Maximum files per repository | `1000` | No |
| `CHUNK_SIZE` | Text chunk size | `1000` | No |
| `CHUNK_OVERLAP` | Chunk overlap size | `200` | No |
| `MAX_CONTEXT_CHUNKS` | Maximum context chunks | `12` | No |
| `SIMILARITY_THRESHOLD` | Similarity threshold | `0.15` | No |
| `ENVIRONMENT` | Environment mode | `development` | No |
| `DEBUG` | Debug mode | `true` | No |

### Frontend Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REACT_APP_API_URL` | Backend API URL | `http://localhost:8000` | Yes |
| `REACT_APP_ENVIRONMENT` | Environment mode | `development` | No |
| `REACT_APP_DEBUG` | Debug mode | `true` | No |
| `REACT_APP_APP_NAME` | Application name | `GitSleuth` | No |
| `REACT_APP_APP_VERSION` | Application version | `1.0.0` | No |

## Troubleshooting

### Common Issues

1. **Backend not starting**: Check if `OPENAI_API_KEY` is set correctly
2. **Frontend can't connect**: Verify `REACT_APP_API_URL` points to the correct backend
3. **CORS errors**: Ensure backend allows requests from frontend domain
4. **Environment variables not loading**: Make sure `.env` files are in the correct directories

### Validation

Test your configuration:

```bash
# Backend
cd backend
python -c "from core.config import settings; print(f'API Key: {settings.openai_api_key[:10]}...')"

# Frontend
cd frontend
npm start
```

## Next Steps

1. Set up your environment variables
2. Test locally with development settings
3. Deploy to your production environment
4. Monitor logs and performance
5. Set up monitoring and alerting
