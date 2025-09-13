# 🕵️ GitSleuth - AI-Powered Code Repository Analyzer

GitSleuth is an intelligent code repository analyzer that uses AI to understand, index, and answer questions about your codebase. Built with FastAPI backend and React frontend, it provides comprehensive insights into any GitHub repository.

## ✨ Features

- 🔍 **Intelligent Repository Analysis**: Automatically downloads and analyzes GitHub repositories
- 🤖 **AI-Powered Q&A**: Ask questions about your codebase and get intelligent answers
- 📊 **Comprehensive Indexing**: Processes multiple file types (Python, JavaScript, TypeScript, etc.)
- 🚀 **Fast Response System**: Optimized for quick query responses with advanced caching
- 🎯 **Context-Aware Answers**: Provides relevant code snippets and file references
- 🔒 **Secure Deployment**: Environment-based configuration for production deployment
- 📱 **Modern UI**: Clean, responsive React frontend with Material-UI components

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **Vector Store**: ChromaDB for semantic search
- **AI Integration**: OpenAI GPT-4 for intelligent responses
- **Repository Processing**: Automatic download and chunking of GitHub repositories
- **Rate Limiting**: Built-in protection against abuse
- **Session Management**: Track indexing progress and user sessions

### Frontend (React + TypeScript)
- **Modern UI**: Material-UI components with responsive design
- **Real-time Updates**: Live indexing progress and status updates
- **Code Highlighting**: Syntax-highlighted code snippets in responses
- **Session Management**: Track and manage multiple repository sessions

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd gitsleuth
   ```

2. **Setup environment:**
   ```bash
   python setup_env.py
   ```

3. **Install backend dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   ```

5. **Configure environment variables:**
   
   **Backend (.env):**
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   HOST=0.0.0.0
   PORT=8000
   ENVIRONMENT=development
   DEBUG=true
   ```
   
   **Frontend (.env):**
   ```env
   REACT_APP_API_URL=http://localhost:8000
   REACT_APP_ENVIRONMENT=development
   REACT_APP_DEBUG=true
   ```

6. **Start the application:**
   
   **Backend:**
   ```bash
   cd backend
   python main.py
   ```
   
   **Frontend:**
   ```bash
   cd frontend
   npm start
   ```

7. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## 📖 Usage

1. **Index a Repository:**
   - Enter a GitHub repository URL
   - Wait for indexing to complete
   - View progress in real-time

2. **Ask Questions:**
   - Use the query interface to ask questions about the codebase
   - Get intelligent answers with code references
   - View syntax-highlighted code snippets

3. **Example Queries:**
   - "Tell me about this project"
   - "How does authentication work?"
   - "Where is the database connection configured?"
   - "What are the main components of this application?"

## 🔧 Configuration

### Environment Variables

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete configuration options.

### Key Settings

- **`OPENAI_API_KEY`**: Your OpenAI API key (required)
- **`REACT_APP_API_URL`**: Backend API URL
- **`MAX_CONTEXT_CHUNKS`**: Number of code chunks to analyze (default: 12)
- **`SIMILARITY_THRESHOLD`**: Similarity threshold for context retrieval (default: 0.15)

## 🐳 Docker Deployment

### Using Docker Compose

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

### Build and Run

```bash
docker-compose up --build
```

## 📁 Project Structure

```
gitsleuth/
├── backend/                 # FastAPI backend
│   ├── core/               # Core configuration and models
│   ├── services/           # Business logic services
│   ├── main.py            # FastAPI application entry point
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Backend environment variables
├── frontend/              # React frontend
│   ├── src/              # Source code
│   │   ├── components/   # React components
│   │   ├── services/     # API services
│   │   └── hooks/        # Custom React hooks
│   ├── package.json      # Node.js dependencies
│   └── .env             # Frontend environment variables
├── .gitignore           # Git ignore rules
├── README.md           # This file
├── DEPLOYMENT_GUIDE.md # Deployment instructions
└── setup_env.py       # Environment setup script
```

## 🔒 Security

- **Environment Variables**: All sensitive data stored in environment variables
- **Rate Limiting**: Built-in protection against API abuse
- **Input Validation**: Comprehensive input validation and sanitization
- **CORS Configuration**: Proper cross-origin resource sharing setup

## 🧪 Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Tests

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

## 📊 API Documentation

When the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /index` - Index a repository
- `GET /status/{session_id}` - Get indexing status
- `POST /query` - Query the codebase
- `DELETE /session/{session_id}` - Delete a session
- `GET /health` - Health check

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- ChromaDB for vector storage
- FastAPI for the backend framework
- React and Material-UI for the frontend
- All contributors and users

## 📞 Support

For support, please open an issue on GitHub or contact the development team.

---

**Made with ❤️ by the GitSleuth Team**
