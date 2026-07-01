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

## Authentication Architecture

Aevix uses a **JWT-based authentication system** with **refresh-token rotation**
and **theft detection**.

### Token Model

| Token | Storage | Lifetime | Use |
|-------|---------|----------|-----|
| **Access Token** | In-memory (Zustand store) | 15 minutes | Bearer auth for API requests |
| **Refresh Token** | HTTP-only cookie (`SameSite=Strict`) | 7 days | Silent rotation of access tokens |

### Flow

1. **Login / Register** — Server validates credentials, creates a refresh-token
   record in the DB (with a unique JTI — JWT ID), sets it as an HTTP-only cookie,
   and returns an access token in the response body.
2. **API Requests** — The client sends the access token via the
   `Authorization: Bearer <token>` header.
3. **Silent Refresh** — When the access token expires (401), the frontend
   client (`frontend/src/lib/api.ts`) automatically calls
   `POST /api/v1/auth/refresh`. The server reads the refresh token from the
   cookie, issues a new access token, **rotates** the refresh token (revokes
   the old one, issues a new one), and sets a new cookie. Concurrent 401s are
   coalesced into a single refresh call.
4. **Boot Re-authentication** — On page load, the Zustand store's
   `initialize()` method attempts a silent refresh. If the session is still
   valid, the user sees no disruption.

### Theft Detection

If a previously-rotated (revoked) refresh token is reused, the server
revokes **all** refresh tokens for that user as a precautionary measure,
terminating every active session.

### Background Cleanup

Expired refresh tokens can be automatically deleted from the database by
setting `REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES` (disabled by default;
opt-in).

### Rate Limiting

Authentication endpoints (`/auth/register`, `/auth/login`,
`/auth/forgot-password`, `/auth/reset-password`) are protected by
Redis-based rate limiting (configurable via
`AUTH_RATE_LIMIT_MAX_REQUESTS` / `AUTH_RATE_LIMIT_WINDOW_SECONDS`).
Rate limiting gracefully degrades (allows requests) when Redis is
unavailable.

### CORS

Cross-Origin Resource Sharing is configured via environment variables:

```
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
BACKEND_CORS_ALLOW_CREDENTIALS=true
```

Set `BACKEND_CORS_ORIGINS=*` to allow all origins (disables credentialed
requests — set `BACKEND_CORS_ALLOW_CREDENTIALS=false` in that case).

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
