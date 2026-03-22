# Research jobs SQLite database module
# Follows history_db.py pattern (raw sqlite3, no ORM)

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict
import os

DB_PATH = Path(os.environ.get("DATA_DIR", "/data")) / "research_jobs.db"


def get_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Initialize research_jobs table."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS research_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            research_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            company_name TEXT NOT NULL,
            person_name TEXT NOT NULL,
            format TEXT NOT NULL DEFAULT 'brief',
            result_json TEXT,
            mail_to TEXT,
            mail_sent INTEGER DEFAULT 0,
            mail_error TEXT,
            error_message TEXT,
            processing_time_s REAL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_research_created_at
        ON research_jobs(created_at DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_research_status
        ON research_jobs(status)
    """)
    conn.commit()
    conn.close()


def save_research(
    research_id: str,
    company_name: str,
    person_name: str,
    fmt: str = "brief",
    status: str = "queued",
    mail_to: Optional[str] = None,
) -> None:
    """Insert a new research job record."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO research_jobs
           (research_id, status, created_at, company_name, person_name, format, mail_to)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            research_id,
            status,
            datetime.now(timezone.utc).isoformat(),
            company_name,
            person_name,
            fmt,
            mail_to,
        ),
    )
    conn.commit()
    conn.close()


def update_research(
    research_id: str,
    status: Optional[str] = None,
    result_json: Optional[str] = None,
    mail_sent: Optional[bool] = None,
    mail_error: Optional[str] = None,
    error_message: Optional[str] = None,
    processing_time_s: Optional[float] = None,
) -> None:
    """Update an existing research job with partial fields."""
    fields = []
    values = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if result_json is not None:
        fields.append("result_json = ?")
        values.append(result_json)
    if mail_sent is not None:
        fields.append("mail_sent = ?")
        values.append(1 if mail_sent else 0)
    if mail_error is not None:
        fields.append("mail_error = ?")
        values.append(mail_error)
    if error_message is not None:
        fields.append("error_message = ?")
        values.append(error_message)
    if processing_time_s is not None:
        fields.append("processing_time_s = ?")
        values.append(processing_time_s)
    # always set completed_at when status transitions to done or failed
    if status in ("done", "failed"):
        fields.append("completed_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())

    if not fields:
        return

    values.append(research_id)
    conn = get_connection()
    conn.execute(
        f"UPDATE research_jobs SET {', '.join(fields)} WHERE research_id = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_research(research_id: str) -> Optional[Dict]:
    """Fetch a single research job by id."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM research_jobs WHERE research_id = ?", (research_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    # parse result_json back to dict if present
    if d.get("result_json"):
        d["result_json"] = json.loads(d["result_json"])
    return d


# auto-init on import
init_db()
