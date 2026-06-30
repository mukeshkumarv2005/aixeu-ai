# Milestone 1: Project Setup — Plan

## Goal
Initialize the Aevix monorepo with production-quality tooling, project structure, and development environment. After this milestone, both the backend and frontend should run in development mode.

## Architecture Overview

```
aevix/
├── backend/          # Python FastAPI application
│   ├── app/
│   │   ├── api/      # Route definitions
│   │   ├── core/     # Config, security, dependencies
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic request/response schemas
│   │   ├── services/ # Business logic
│   │   └── main.py   # FastAPI entrypoint
│   ├── alembic/      # Database migrations
│   ├── tests/        # Pytest tests
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/         # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── features/    # Feature modules
│   │   ├── hooks/       # Custom React hooks
│   │   ├── lib/         # Utilities
│   │   ├── stores/      # Zustand stores
│   │   ├── pages/       # Route pages
│   │   └── main.tsx     # Entrypoint
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
├── docker/
│   ├── nginx/
│   │   └── default.conf
│   └── docker-compose.yml
├── scripts/          # Utility scripts
├── docs/             # Documentation
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

## Why These Choices

| Choice | Rationale |
|--------|-----------|
| **FastAPI** | Async-native, auto-docs, Pydantic validation — Python's best API framework for AI workloads |
| **SQLAlchemy 2.0** | Mature, async-capable ORM with Alembic migrations |
| **Vite** | Fastest React dev server, native ESM, instant HMR |
| **Tailwind CSS** | Utility-first, tree-shaking, consistent design system |
| **Zustand** | Minimal state management, works outside React, TypeScript-native |
| **TanStack Query** | Server state cache, deduplication, background refetch |
| **Docker Compose** | Single-command local dev with PostgreSQL + Redis |

## Implementation Steps

### Step 1: Root project files
- `.gitignore` (Python, Node, Docker, OS artifacts)
- `LICENSE` (MIT)
- `README.md` (project overview, quick start)
- `.env.example` (all required env vars with safe defaults)

### Step 2: Backend scaffolding
- `backend/pyproject.toml` with pinned dependencies
- `backend/app/__init__.py`, `app/main.py` (minimal FastAPI app)
- `backend/app/core/config.py` (Pydantic Settings)
- `backend/app/core/security.py` (password hashing, JWT primitives — foundation)
- `backend/app/api/__init__.py`, `api/v1/__init__.py`
- Health check endpoint (`GET /api/v1/health`)
- `backend/Dockerfile` (multi-stage, production-optimized)
- `backend/.env.example`

### Step 3: Frontend scaffolding
- Scaffold with `npm create vite@latest` (React + TypeScript)
- Install and configure: Tailwind CSS, React Router, Zustand, TanStack Query, React Hook Form
- App shell with Router setup
- Dark mode setup (CSS variables, Tailwind dark mode)
- `frontend/Dockerfile` (multi-stage with nginx)
- `frontend/vite.config.ts` with proxy to backend

### Step 4: Docker infrastructure
- `docker/docker-compose.yml` (backend, frontend, postgres, redis)
- `docker/nginx/default.conf` (reverse proxy in production)
- `docker/.env.example`

### Step 5: CI / Scripts
- `.github/workflows/ci.yml` (backend tests, frontend build)
- `scripts/dev.sh` (start everything in dev mode)

### Step 6: Verification
- Backend starts and health endpoint responds
- Frontend compiles and dev server loads
- Docker Compose services start
- Tests pass

## Services (Docker Compose)

| Service | Port | Purpose |
|---------|------|---------|
| frontend | 3000 | Vite dev server (hot reload) |
| backend | 8000 | FastAPI + auto-docs at /docs |
| postgres | 5432 | Primary database |
| redis | 6379 | Caching + Celery/queue |

## Files to Create (33 total)

Root (5): `.gitignore`, `LICENSE`, `README.md`, `.env.example`, `PLAN.md`
Backend (12): `pyproject.toml`, `Dockerfile`, `app/__init__.py`, `app/main.py`, `app/core/__init__.py`, `app/core/config.py`, `app/core/security.py`, `app/api/__init__.py`, `app/api/v1/__init__.py`, `app/api/v1/health.py`, `tests/__init__.py`, `tests/test_health.py`
Frontend (10): (scaffolded by Vite then customized)
Docker (4): `docker-compose.yml`, `nginx/default.conf`, `.dockerignore`, `.env.example`
Meta (2): `scripts/dev.sh`, `.github/workflows/ci.yml`

---

**After approval, I will:**
1. Create each file with production-quality code
2. Install dependencies
3. Verify everything compiles and starts
4. Write the first commit
