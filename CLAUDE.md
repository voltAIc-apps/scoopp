# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Scoopp

Web crawling and company research microservice built on Crawl4AI with FastAPI. Three services: backend (FastAPI on port 8002), web-UI (Vue.js on port 3000), and Redis (port 6379). Deployed via Docker Compose on a bridge network (`scoopp-net`).

## Build & Run

```bash
cp .env.example .env          # fill in API keys
docker compose up -d           # start all services
docker compose up --build      # rebuild and start
```

Backend: http://10.0.99.1:8002 | API docs: http://10.0.99.1:8002/docs
Web-UI: http://10.0.99.1:3000

### Local development (without Docker)

```bash
# Backend (Python 3.12+, Redis must be running)
cd app && pip install -r requirements.txt && python server.py

# Frontend
cd web-UI && npm install && npm run dev
```

### Frontend production build
```bash
cd web-UI && npm run build    # output to dist/
```

## Tests

```bash
python tests/test_depth_crawl.py
python tests/debug_results.py
```

No linter or formatter is configured.

## Architecture

### Backend (`app/`)

- **server.py** — FastAPI app entry point. Mounts routers, sets up CORS, rate limiting (SlowAPI), Prometheus metrics, Redis pool, global page semaphore, and browser pool janitor.
- **api.py** — Core crawl request handlers (`/crawl`, `/md`, `/html`, `/screenshot`, `/pdf`, `/crawl/stream`, `/history`, LinkedIn endpoints).
- **job.py** — Async job routing: enqueue long-running crawl/LLM jobs via `BackgroundTasks`, poll results via job ID.
- **schemas.py** — Pydantic models for all request/response payloads.
- **auth.py** — JWT token auth (disabled by default) and `X-API-Key` verification for research endpoints.
- **crawler_pool.py** — Browser instance pooling with memory-aware allocation (95% threshold), idle timeout (30 min), and global semaphore (max 40 concurrent pages).
- **history_db.py** — SQLite module for crawl history persistence.
- **research_db.py** — SQLite module for research job persistence.
- **config.yml** — Central configuration (app, LLM, Redis, CORS, rate limiting, crawler pool, S3).

### Research Pipeline (`app/routers/research.py` + `app/services/`)

Five-step async pipeline (spec: `specs/001_research_pipeline.md`):
1. Company URL discovery via Brave Search (`brave_search.py`)
2. Website crawl + LLM field extraction (`researcher.py`)
3. LinkedIn profile lookup (`brave_search.py`)
4. Markdown persistence to S3/MinIO (`s3_storage.py`)
5. Optional email dispatch via Brevo/SendGrid (`mailer.py`)

### Frontend (`web-UI/`)

Vue 3 + Vite + Pinia. State in `stores/crawl.js`, API client in `api/scoopp.js`. Routes: `/` (crawl form), `/history` (crawl history). Served by Nginx in production (multi-stage Docker build).

### Data Storage

- **SQLite** (`data/crawl_history.db`, `data/research_jobs.db`) — structured data
- **S3/MinIO** (`md/{crawl_id}/{domain}/{timestamp}.md`) — crawled markdown
- **Redis** — task queue, session cache (7-day TTL default)

## Key Configuration

- `app/config.yml` — all backend settings (ports, pool limits, timeouts, LLM provider)
- `.env` — secrets (API keys, S3 credentials, mail config). See `.env.example`.
- `docker-compose.yaml` — service definitions, port mappings, volume mounts
- `web-UI/nginx.conf` — frontend reverse proxy config
- `app/supervisord.conf` — in-container process management (gunicorn + redis-server)

## Container Images

Backend Dockerfile: Python 3.12-slim + Crawl4AI 0.6.0 + Chromium (Playwright). Runs as non-root `appuser`. Gunicorn with Uvicorn workers.

Web-UI Dockerfile: Node 20 Alpine (build) → Nginx Alpine (serve).

Container registry: `crepo.re-cloud.io` (credentials: `cc:bskSkOPLF4ziny5`).
