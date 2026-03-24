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
cp .env.example .env   # fill in API keys (SECRET_KEY is required)
docker compose up -d
```

Backend: https://scoopp.re-cloud.io/api
Web-UI: https://scoopp.re-cloud.io
API docs: https://scoopp.re-cloud.io/api/docs

## Authentication

All API endpoints require a JWT token, except `/health`, `/token`, and `/docs`.

### 1. Get a token

```bash
curl -X POST https://scoopp.re-cloud.io/api/token \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'
```

Response:

```json
{
  "email": "you@example.com",
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### 2. Use the token

Pass the token in the `Authorization` header on all subsequent requests:

```bash
# Extract markdown from a URL
curl -X POST https://scoopp.re-cloud.io/api/md \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"url": "https://example.com", "f": "fit"}'

# Crawl with depth
curl -X POST https://scoopp.re-cloud.io/api/crawl \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -d '{"urls": ["https://example.com"], "max_depth": 2, "max_pages": 10}'

# Get crawl history
curl -H "Authorization: Bearer eyJ..." \
  https://scoopp.re-cloud.io/api/history
```

### Token details

- Tokens expire after **60 minutes**. Request a new one when you get a `401` response.
- The `/token` endpoint is rate-limited to **10 requests per minute**.
- All other endpoints are rate-limited to **100 requests per minute**.

### Research endpoints

Research endpoints require an additional `X-API-Key` header (set via `API_KEY` env var):

```bash
curl -X POST https://scoopp.re-cloud.io/api/research \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ..." \
  -H "X-API-Key: your-api-key" \
  -d '{"company_name": "Acme Corp"}'
```

## API endpoints

### Crawling (JWT required)
- `POST /crawl` — multi-URL or depth crawl
- `POST /crawl/stream` — streaming crawl (NDJSON)
- `POST /md` — single URL markdown extraction
- `POST /html` — HTML extraction
- `POST /screenshot` — page screenshot
- `POST /pdf` — PDF export

### Research (JWT + X-API-Key required)
- `POST /research` — company enrichment pipeline
- `GET /research/{id}` — poll research result

### Jobs (JWT required)
- `POST /llm/job` — enqueue LLM extraction
- `GET /llm/job/{id}` — poll LLM result
- `POST /crawl/job` — enqueue crawl
- `GET /crawl/job/{id}` — poll crawl result

### History (JWT required)
- `GET /history` — crawl history list
- `GET /history/{crawl_id}` — single crawl details

### LinkedIn (JWT required)
- `POST /auth/linkedin/login` — login and store session
- `POST /crawl/linkedin` — crawl LinkedIn profiles

### Public (no auth)
- `POST /token` — get a JWT token
- `GET /health` — health check
- `GET /docs` — Swagger API docs

### Restricted
- `GET /metrics` — Prometheus metrics (blocked externally, internal access only)

## Environment variables

See `.env.example` for required configuration. Key variables:

- `SECRET_KEY` — **Required.** JWT signing key. App will not start without it.
- `API_KEY` — Required for `/research` endpoints.
- `OPENAI_API_KEY` — LLM extraction.
- `BRAVE_API_KEY` — Company URL discovery.

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
k8s/              Kubernetes manifests
```
