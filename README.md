# Aevix

**Your Intelligent AI Workspace**

Aevix is an AI-powered productivity workspace that combines AI Chat, Document Intelligence, AI Agents, Knowledge Management, Task Management, and more — all inside one modern application.

## Features

- **AI Chat** — Streaming responses, markdown, conversation history, and export
- **Document Intelligence** — Upload, OCR, summarize, Q&A with citation support
- **Knowledge Base** — Semantic search, folders, tags, bookmarks, personal memory
- **AI Agents** — Research, Writing, Coding, Data Analysis, Document, Planning
- **Task Manager** — Projects, deadlines, priorities, Kanban board, calendar view
- **Global Search** — Semantic search across all content types
- **Workspace** — Notes, bookmarks, files, personal memory, knowledge graph

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Zustand, TanStack Query |
| **Backend** | Python 3.14, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic |
| **Database** | PostgreSQL 16, Redis 7 |
| **Vector** | pgvector (PostgreSQL extension) |
| **AI** | LLM APIs, Embeddings, RAG, Multi-Agent |
| **Infra** | Docker, Docker Compose, Nginx, GitHub Actions |

## Quick Start

**Prerequisites:** Python 3.14+, Node.js 22+, Docker Desktop

```bash
# Clone and enter
git clone https://github.com/your-org/aevix.git
cd aevix

# Start all services (PostgreSQL, Redis, backend, frontend)
docker compose -f docker/docker-compose.yml up -d

# Or run locally:
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Frontend:** http://localhost:3000

## Project Structure

```
aevix/
├── backend/          # Python FastAPI application
├── frontend/         # React + TypeScript + Vite
├── agents/           # AI Agent implementations
├── docker/           # Docker Compose and Nginx configs
├── scripts/          # Utility scripts
├── docs/             # Documentation
├── tests/            # Integration and E2E tests
├── .github/          # GitHub Actions workflows
```

## Documentation

- [Architecture Guide](docs/architecture.md)
- [API Guide](docs/api.md)
- [Database Guide](docs/database.md)
- [Deployment Guide](docs/deployment.md)
- [Developer Guide](docs/developer.md)

## License

[MIT](LICENSE)
