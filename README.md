# 🕸️ Crawl4AI FastAPI Service

This project exposes [`crawl4ai`](https://pypi.org/project/crawl4ai/) as a Dockerized microservice with a FastAPI interface for programmatically crawling web content and storing results as sanitized Markdown files. It supports crawl depth and timeout controls per request, persistent crawl status storage via SQLite, logging, and is ready for Celery integration.

---

## 🛠 Features

* FastAPI-based web service for managing crawls
* Persistent crawl ID and status tracking using SQLite
* Configurable and per-request crawl depth and timeout
* HTML sanitization using `bleach`
* Persistent logs written to `/data/crawl4ai.log`
* File-based crawl results (`/data/<crawl_id>.md`)
* Configurable via `crawl.config`
* Dockerized setup with `docker-compose`

---

## 📁 Project Structure

```
crawl4ai-service/
├── app/                 # FastAPI backend and logic
│   ├── main.py
│   ├── models.py
│   ├── utils.py
│   ├── db.py
│   └── auth_dummy.py
├── data/                # Output files + logs + sqlite db
├── crawl.config         # Default settings (depth, timeout)
├── requirements.txt
├── Dockerfile
└── docker-compose.yaml
```

---

## 🚀 Quickstart

### 1. Build & Run

```bash
docker-compose up --build
```

### 2. Test API (with curl)

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "crawl_depth": 2, "crawl_timeout": 5}'
```

---

## 🧩 Configuration

Edit `crawl.config`:

```ini
[settings]
crawl_depth = 2        # Default max crawl depth
crawl_timeout = 10     # Default timeout per crawl (seconds)
```

---

## 📜 API Endpoints

| Endpoint             | Method | Description                        |
| -------------------- | ------ | ---------------------------------- |
| `/crawl`             | POST   | Trigger a new crawl                |
| `/status/{crawl_id}` | GET    | Check crawl status                 |
| `/result/{crawl_id}` | GET    | Retrieve sanitized Markdown result |
| `/list`              | GET    | List all stored `.md` results      |
| `/health`            | GET    | Simple health check                |

---

## 🛡️ Security & Improvements

* [ ] Add authentication (OAuth2 or API Key)
* [ ] Replace file-based crawl ID with atomic SQLite sequence
* [ ] Add CORS headers for browser clients
* [ ] Integrate Celery for background queueing (SQLite → Redis)
* [ ] Implement file size limits / storage cleanup policies

---

![image](https://github.com/user-attachments/assets/6bdc10ef-082d-4b77-a52b-ced7b461bc18)

---
# Around the Planet

https://github.com/zaidmukaddam/scira
https://exa.sh/

<img width="1290" height="842" alt="image" src="https://github.com/user-attachments/assets/d4f02302-636a-4fb3-97ca-644f5d0bd0ff" />
