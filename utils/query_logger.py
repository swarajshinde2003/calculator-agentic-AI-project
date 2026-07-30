"""
Per-query SQLite logger.

Every call to the /query endpoint writes one row to
  <project_root>/logs/calculator_queries.db

Schema
------
id            INTEGER  PK autoincrement
request_id    TEXT     UUID generated per request
timestamp     TEXT     ISO-8601 UTC
question      TEXT     raw user question
answer        TEXT     final assistant answer (NULL on error)
tools_used    TEXT     JSON array of {tool, args} objects
token_usage   TEXT     JSON object {prompt_tokens, completion_tokens, total_tokens} or NULL
latency_ms      REAL     wall-clock time for the full /query call
status          TEXT     "success" | "error"
error_message   TEXT     exception string (NULL on success)
conversation_id TEXT     Streamlit chat ID (enables per-session filtering in LangSmith)
user_id         TEXT     Streamlit session user ID (enables per-user filtering in LangSmith)
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = _PROJECT_ROOT / "logs" / "calculator_queries.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS queries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id    TEXT    NOT NULL,
    timestamp     TEXT    NOT NULL,
    question      TEXT    NOT NULL,
    answer        TEXT,
    tools_used    TEXT,
    token_usage   TEXT,
    latency_ms    REAL,
    status          TEXT    NOT NULL,
    error_message   TEXT,
    conversation_id TEXT,
    user_id         TEXT
)
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db() -> None:
    """Create the queries table and add any missing columns (safe to call repeatedly)."""
    with _connect() as conn:
        conn.execute(_CREATE_TABLE_SQL)
        # Migrate existing databases: add new columns when they are absent.
        for col in ("conversation_id", "user_id"):
            try:
                conn.execute(f"ALTER TABLE queries ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists — nothing to do.
        conn.commit()
    logger.info("SQLite query log ready at %s", DB_PATH)


def log_query(
    *,
    request_id: str,
    question: str,
    answer: Optional[str],
    tools_used: List[Dict[str, Any]],
    token_usage: Optional[Dict[str, Any]],
    latency_ms: float,
    status: str,
    error_message: Optional[str] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Insert one row for the completed query. Errors are caught and logged."""
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO queries
                    (request_id, timestamp, question, answer,
                     tools_used, token_usage, latency_ms, status, error_message,
                     conversation_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    datetime.now(timezone.utc).isoformat(),
                    question,
                    answer,
                    json.dumps(tools_used),
                    json.dumps(token_usage) if token_usage is not None else None,
                    latency_ms,
                    status,
                    error_message,
                    conversation_id,
                    user_id,
                ),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write query log row: %s", exc)
