# Crawl history SQLite database module
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import os

DB_PATH = Path(os.environ.get("DATA_DIR", "/data")) / "crawl_history.db"

def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crawl_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_id TEXT UNIQUE NOT NULL,
            request_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            urls TEXT NOT NULL,
            success INTEGER,
            error_message TEXT,
            max_depth INTEGER,
            pages_crawled INTEGER,
            processing_time_s REAL,
            markdown_preview TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at
        ON crawl_history(created_at DESC)
    """)
    conn.commit()
    conn.close()

def save_crawl(
    crawl_id: str,
    request_type: str,
    urls: List[str],
    status: str,
    success: bool,
    error_message: Optional[str] = None,
    max_depth: Optional[int] = None,
    pages_crawled: int = 0,
    processing_time: Optional[float] = None,
    markdown_preview: Optional[str] = None
) -> None:
    """Save crawl request to history."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO crawl_history
        (crawl_id, request_type, status, created_at, urls, success,
         error_message, max_depth, pages_crawled, processing_time_s, markdown_preview)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        crawl_id,
        request_type,
        status,
        datetime.utcnow().isoformat(),
        json.dumps(urls),
        1 if success else 0,
        error_message,
        max_depth,
        pages_crawled,
        processing_time,
        markdown_preview[:500] if markdown_preview else None
    ))
    conn.commit()
    conn.close()

def get_history(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get crawl history list."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT crawl_id, request_type, status, created_at, urls,
               success, pages_crawled, processing_time_s, markdown_preview
        FROM crawl_history
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()

    return [
        {
            "crawl_id": row["crawl_id"],
            "request_type": row["request_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "urls": json.loads(row["urls"]),
            "success": bool(row["success"]),
            "pages_crawled": row["pages_crawled"],
            "processing_time_s": row["processing_time_s"],
            "markdown_preview": row["markdown_preview"]
        }
        for row in rows
    ]

def get_crawl(crawl_id: str) -> Optional[Dict]:
    """Get single crawl details."""
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM crawl_history WHERE crawl_id = ?
    """, (crawl_id,)).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "crawl_id": row["crawl_id"],
        "request_type": row["request_type"],
        "status": row["status"],
        "created_at": row["created_at"],
        "urls": json.loads(row["urls"]),
        "success": bool(row["success"]),
        "error_message": row["error_message"],
        "max_depth": row["max_depth"],
        "pages_crawled": row["pages_crawled"],
        "processing_time_s": row["processing_time_s"],
        "markdown_preview": row["markdown_preview"]
    }

# Initialize database on module import
init_db()
