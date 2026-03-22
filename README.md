# Scoopp

Web crawling and company research microservice built on crawl4ai with FastAPI.

## Services

| Service | Port | Description |
|---------|------|-------------|
| Backend (FastAPI) | 8002 | Crawl, research, LLM extraction endpoints |
| Web-UI (Vue.js) | 3000 | Crawl interface with history |
| Redis | 6379 | Task queue, session cache |

## Quick start

```bash
cp .env.example .env   # fill in API keys
docker compose up -d
```

Backend: http://10.0.99.1:8002
Web-UI: http://10.0.99.1:3000
API docs: http://10.0.99.1:8002/docs

## API endpoints

### Crawling
- `POST /crawl` — multi-URL or depth crawl
- `POST /crawl/stream` — streaming crawl (NDJSON)
- `POST /md` — single URL markdown extraction
- `POST /html` — HTML extraction
- `POST /screenshot` — page screenshot
- `POST /pdf` — PDF export

### Research (spec: specs/001_research_pipeline.md)
- `POST /research` — company enrichment pipeline (requires X-API-Key)
- `GET /research/{id}` — poll research result

### Jobs (async)
- `POST /llm/job` — enqueue LLM extraction
- `GET /llm/job/{id}` — poll LLM result
- `POST /crawl/job` — enqueue crawl
- `GET /crawl/job/{id}` — poll crawl result

### History
- `GET /history` — crawl history list
- `GET /history/{crawl_id}` — single crawl details

### LinkedIn
- `POST /auth/linkedin/login` — login and store session
- `POST /crawl/linkedin` — crawl LinkedIn profiles

### System
- `GET /health` — health check
- `GET /metrics` — Prometheus metrics

## Environment variables

See `.env.example` for required configuration.

## Project structure

```
app/              Backend (FastAPI + Python)
  routers/        Route handlers
  services/       Business logic (researcher, mailer, brave_search)
  models/         Pydantic models
web-UI/           Frontend (Vue.js + Vite)
specs/            Feature specifications
tests/            Test suite
data/             Runtime data (SQLite, mounted volume)
```
